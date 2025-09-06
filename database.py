# database.py - الدوال الأساسية للبيانات
from models import db, User, Room, UserRoom, Message
from datetime import datetime
#from supabase import create_client
import os
import re

def init_supabase():
    return create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_KEY'])

# ==================== دوال المستخدمين ====================
def get_user_by_id(user_id):
    return User.query.get(user_id)

def get_user_by_email(email):
    return User.query.filter_by(email=email).first()

def get_user_by_username(username):
    return User.query.filter_by(username=username).first()

def update_user_online_status(user_id, is_online):
    user = User.query.get(user_id)
    if user:
        user.is_online = is_online
        user.last_seen = datetime.utcnow()
        db.session.commit()
        return True
    return False

def get_active_users():
    return User.query.filter_by(is_online=True).order_by(User.username).all()

def search_users(query):
    return User.query.filter(User.username.ilike(f'%{query}%')).order_by(User.username).limit(20).all()

def create_user_with_validation(username, email, password):
    if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
        raise ValueError('اسم المستخدم غير صحيح')
    
    if not re.match(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$', email):
        raise ValueError('البريد الإلكتروني غير صحيح')
    
    user = User(username=username, email=email, password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()
    return user

# ==================== دوال الغرف ====================
def get_room_by_id(room_id):
    return Room.query.get(room_id)

def get_room_by_name(room_name):
    return Room.query.filter_by(name=room_name).first()

def create_room(name, description, created_by, is_public=True):
    if not re.match(r'^[a-zA-Z0-9_]{3,100}$', name):
        raise ValueError('اسم الغرفة غير صحيح')
    
    room = Room(name=name, description=description, created_by=created_by, is_public=is_public)
    db.session.add(room)
    db.session.commit()
    return room

def get_user_rooms(user_id):
    return Room.query.join(UserRoom).filter(UserRoom.user_id == user_id).all()

def add_user_to_room(user_id, room_id):
    # التحقق إذا كان المستخدم مضافاً بالفعل
    existing = UserRoom.query.filter_by(user_id=user_id, room_id=room_id).first()
    if not existing:
        user_room = UserRoom(user_id=user_id, room_id=room_id)
        db.session.add(user_room)
        db.session.commit()
        return True
    return False

def remove_user_from_room(user_id, room_id):
    user_room = UserRoom.query.filter_by(user_id=user_id, room_id=room_id).first()
    if user_room:
        db.session.delete(user_room)
        db.session.commit()
        return True
    return False

def get_room_members(room_id):
    return User.query.join(UserRoom).filter(UserRoom.room_id == room_id).all()

# ==================== دوال الرسائل ====================
def save_message(room_id, user_id, username, content, message_type='text', is_private=False, recipient_id=None):
    message = Message(
        room_id=room_id,
        user_id=user_id,
        username=username,
        content=content,
        message_type=message_type,
        is_private=is_private,
        recipient_id=recipient_id
    )
    db.session.add(message)
    db.session.commit()
    
    # تحديث وقت آخر قراءة للمستخدم
    update_last_read(user_id, room_id)
    
    # إشعار Realtime
    notify_new_message(message)
    return message

def get_room_messages(room_id, limit=100, since=None):
    query = Message.query.filter_by(room_id=room_id, is_private=False)
    if since:
        query = query.filter(Message.timestamp > since)
    return query.order_by(Message.timestamp.desc()).limit(limit).all()

def get_private_messages(user_id, recipient_id, limit=100):
    return Message.query.filter(
        ((Message.user_id == user_id) & (Message.recipient_id == recipient_id)) |
        ((Message.user_id == recipient_id) & (Message.recipient_id == user_id))
    ).order_by(Message.timestamp.desc()).limit(limit).all()

def get_recent_messages(room_id, since=None):
    query = Message.query.filter_by(room_id=room_id)
    if since:
        query = query.filter(Message.timestamp > since)
    return query.order_by(Message.timestamp.desc()).limit(50).all()

def get_unread_count(room_id, user_id):
    user_room = UserRoom.query.filter_by(user_id=user_id, room_id=room_id).first()
    if user_room:
        return Message.query.filter(
            Message.room_id == room_id,
            Message.timestamp > user_room.last_read
        ).count()
    return 0

def update_last_read(user_id, room_id):
    user_room = UserRoom.query.filter_by(user_id=user_id, room_id=room_id).first()
    if user_room:
        user_room.last_read = datetime.utcnow()
        db.session.commit()
        return True
    return False

# ==================== دوال Realtime ====================
def notify_new_message(message):
    try:
        supabase = init_supabase()
        
        channel_name = f'room_{message.room_id}' if not message.is_private else f'private_{message.user_id}_{message.recipient_id}'
        
        supabase.channel(channel_name).send({
            'type': 'broadcast',
            'event': 'new_message',
            'payload': {
                'id': message.id,
                'room_id': message.room_id,
                'user_id': message.user_id,
                'username': message.username,
                'content': message.content,
                'message_type': message.message_type,
                'is_private': message.is_private,
                'recipient_id': message.recipient_id,
                'timestamp': message.timestamp.isoformat()
            }
        })
    except Exception as e:
        print(f"Error in notify_new_message: {e}")

def subscribe_to_room(room_id, callback):
    try:
        supabase = init_supabase()
        
        subscription = supabase.channel(f'room_{room_id}') \
            .on('postgres_changes', {
                'event': 'INSERT',
                'schema': 'public',
                'table': 'messages',
                'filter': f'room_id=eq.{room_id}'
            }, callback) \
            .subscribe()
        
        return subscription
    except Exception as e:
        print(f"Error in subscribe_to_room: {e}")
        return None
#تحسينات
def get_user_with_rooms(user_id):
    """الحصول على المستخدم مع غرفه"""
    user = User.query.get(user_id)
    if user:
        return {
            'user': user,
            'rooms': user.room_memberships
        }
    return None

def create_room_with_owner(name, description, created_by_id, is_public=True):
    """إنشاء غرفة وإضافة المالك لها"""
    try:
        # إنشاء الغرفة
        room = Room(
            name=name,
            description=description,
            created_by=created_by_id,
            is_public=is_public
        )
        db.session.add(room)
        db.session.flush()  # للحصول على ID قبل commit
        
        # إضافة المالك إلى الغرفة
        user_room = UserRoom(user_id=created_by_id, room_id=room.id)
        db.session.add(user_room)
        
        db.session.commit()
        return room
        
    except Exception as e:
        db.session.rollback()
        raise e

def get_room_with_members(room_id):
    """الحصول على الغرفة مع أعضائها"""
    room = Room.query.get(room_id)
    if room:
        return {
            'room': room,
            'members': room.members,
            'message_count': len(room.messages)
        }
    return None        