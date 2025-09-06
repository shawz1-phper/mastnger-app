from flask import Flask, render_template, request, jsonify, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_cors import CORS
import json
import os
import base64
import hashlib
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import secrets
from functools import wraps
from dotenv import load_dotenv
import logging
from supabase_client import supabase
from models import db, User, Room, UserRoom, Message
# app.py - في الأعلى مع الاستيرادات
from database import (
    get_user_by_id, get_user_by_email, get_user_by_username,
    update_user_online_status, get_active_users, search_users,
    create_user_with_validation, get_room_by_id, get_room_by_name,
    create_room, get_user_rooms, add_user_to_room, remove_user_from_room,
    get_room_members, save_message, get_room_messages, get_private_messages,
    get_recent_messages, get_unread_count, update_last_read,
    notify_new_message, subscribe_to_room
)
from utils import generate_password, is_valid_email, is_valid_username, format_timestamp

# ثم استخدم الدوال في routes كما في الأمثلة السابقة

# تحميل متغيرات البيئة
load_dotenv()

# تهيئة التطبيق
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-'+secrets.token_hex(16))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SOCKETIO_ASYNC_MODE'] = 'threading'  # الخيار الأفضل
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SUPABASE_DB_URL').replace('postgres://', 'postgresql://')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
# تهيئة SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode=app.config['SOCKETIO_ASYNC_MODE'])
CORS(app)

# إعداد Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'يجب تسجيل الدخول للوصول إلى هذه الصفحة'
# إعداد التشفير
def generate_encryption_key():
    key = os.environ.get('ENCRYPTION_KEY')
    if not key:
        key = Fernet.generate_key().decode()
        os.environ['ENCRYPTION_KEY'] = key
    return key

encryption_key = generate_encryption_key()
cipher_suite = Fernet(encryption_key.encode())


# إضافة فلاتر Jinja2 المخصصة
@app.template_filter('time_ago')
def time_ago_filter(datetime_str):
    if not datetime_str:
        return "غير معروف"
    
    try:
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        now = datetime.now(dt.tzinfo if dt.tzinfo else None)
        diff = now - dt
        
        if diff.days > 365:
            years = diff.days // 365
            return f"منذ {years} سنة"
        elif diff.days > 30:
            months = diff.days // 30
            return f"منذ {months} شهر"
        elif diff.days > 0:
            return f"منذ {diff.days} يوم"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"منذ {hours} ساعة"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"منذ {minutes} دقيقة"
        else:
            return "الآن"
    except:
        return "غير معروف"


# app.py - إعداد ذكي للاتصال بقاعدة البيانات
def setup_database():
    """إعداد اتصال قاعدة البيانات الذكي"""
    
    # إذا كان هناك Supabase config، استخدمه
    if os.environ.get('SUPABASE_URL') and os.environ.get('SUPABASE_KEY'):
        print("🚀 Using Supabase PostgreSQL database")
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
        
        # تعطيل إنشاء الجداول التلقائي لـ SQLite
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
    else:
        print("💻 Using local SQLite database for development")
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
        
        # تهيئة SQLite المحلي
        init_database()

# استدعاء الإعداد الذكي
setup_database()
# بعد تعريف app



# نموذج المستخدم
class User(UserMixin):
    def __init__(self, id, username, email, password, avatar='default.png', theme='light', last_seen=None):
        self.id = id
        self.username = username
        self.email = email
        self.password = password
        self.avatar = avatar
        self.theme = theme
        self.last_seen = last_seen or datetime.now().isoformat()

    def get_avatar_url(self):
        return f"/static/img/avatars/{self.avatar}"

# دوال مساعدة للتعامل مع البيانات
def get_data_path(filename):
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, filename)

def load_json_data(filename, default=None):
    if default is None:
        default = {}
    data_path = get_data_path(filename)
    try:
        if os.path.exists(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logging.error(f"Error loading {filename}: {e}")
    return default

def save_json_data(filename, data):
    data_path = get_data_path(filename)
    try:
        with open(data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        logging.error(f"Error saving {filename}: {e}")
        return False

def create_backup(filename):
    data = load_json_data(filename)
    if data:
        backup_dir = get_data_path('backups')
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = os.path.join(backup_dir, f"{filename}_{timestamp}.json")
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

# دوال التشفير
def encrypt_message(message):
    try:
        encrypted_message = cipher_suite.encrypt(message.encode())
        return base64.urlsafe_b64encode(encrypted_message).decode()
    except Exception as e:
        logging.error(f"Encryption error: {e}")
        return message

def decrypt_message(encrypted_message):
    try:
        decoded_message = base64.urlsafe_b64decode(encrypted_message.encode())
        decrypted_message = cipher_suite.decrypt(decoded_message).decode()
        return decrypted_message
    except Exception as e:
        logging.error(f"Decryption error: {e}")
        return encrypted_message


# استبدال دوال التحميل والحفظ
def load_users():
    try:
        response = supabase.get_client().table('users').select('*').execute()
        return {str(user['id']): user for user in response.data}
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}

def save_users(users_dict):
    try:
        # Convert dict to list
        users_list = list(users_dict.values())
        response = supabase.get_client().table('users').upsert(users_list).execute()
        return True
    except Exception as e:
        print(f"Error saving users: {e}")
        return False

def load_messages():
    try:
        response = supabase.get_client().table('messages').select('*').execute()
        return {"rooms": {}, "private": {}}  # سنعدل هذا لاحقاً
    except Exception as e:
        print(f"Error loading messages: {e}")
        return {"rooms": {}, "private": {}}

def save_message(message_data):
    try:
        response = supabase.get_client().table('messages').insert({
            'room_name': message_data.get('room'),
            'user_id': message_data.get('user_id'),
            'username': message_data.get('username'),
            'content': message_data.get('message'),
            'timestamp': datetime.now().isoformat(),
            'is_private': message_data.get('is_private', False),
            'recipient_id': message_data.get('recipient_id')
        }).execute()
        return True
    except Exception as e:
        print(f"Error saving message: {e}")
        return False
def load_rooms():
    return load_json_data('rooms.json', {})

def save_rooms(rooms):
    create_backup('rooms.json')
    return save_json_data('rooms.json', rooms)

@socketio.on('connect')
def handle_connect():
    print('✅ Client connected!')
    emit('connected', {'status': 'connected'})

@socketio.on('disconnect')
def handle_disconnect():
    print('❌ Client disconnected')
# في app.py أضف
@app.before_request
def check_memory():
    import psutil
    memory = psutil.virtual_memory()
    print(f'🧠 Memory usage: {memory.percent}%')
# إدارة تحميل المستخدم
@login_manager.user_loader
def load_user(user_id):
    users = load_users()
    user_data = users.get(user_id)
    if user_data:
        return User(user_id, 
                   user_data['username'], 
                   user_data['email'], 
                   user_data['password'],
                   user_data.get('avatar', 'default.png'),
                   user_data.get('theme', 'light'),
                   user_data.get('last_seen'))
    return None

# دوال المصادقة
def login_required_socket(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            emit('error', {'message': 'Authentication required'})
            return
        return f(*args, **kwargs)
    return wrapped

# المسارات
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        users = load_users()
        email = request.form.get('email')
        password = request.form.get('password')
        remember = bool(request.form.get('remember'))
        
        for user_id, user_data in users.items():
            if user_data['email'] == email and check_password_hash(user_data['password'], password):
                user = User(user_id, user_data['username'], email, user_data['password'])
                login_user(user, remember=remember)
                
                # تحديث وقت آخر زيارة
                users[user_id]['last_seen'] = datetime.now().isoformat()
                save_users(users)
                
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard'))
        
        return render_template('login.html', error='البريد الإلكتروني أو كلمة المرور غير صحيحة')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # تحميل المستخدمين الحاليين من Supabase
        users = load_users()
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            return render_template('register.html', error='كلمات المرور غير متطابقة')
        
        if len(password) < 6:
            return render_template('register.html', error='كلمة المرور يجب أن تكون على الأقل 6 أحرف')
        
        # التحقق من عدم وجود مستخدم بنفس البريد أو اسم المستخدم
        for user_id, user_data in users.items():
            if user_data['email'] == email:
                return render_template('register.html', error='البريد الإلكتروني مسجل مسبقاً')
            if user_data['username'] == username:
                return render_template('register.html', error='اسم المستخدم مسجل مسبقاً')
        
        # إنشاء مستخدم جديد في Supabase
        try:
            # إدخال المستخدم الجديد مباشرة في Supabase
            response = supabase.get_client().table('users').insert({
                'username': username,
                'email': email,
                'password': generate_password_hash(password),
                'avatar': 'default.png',
                'theme': 'light',
                'joined_at': datetime.now().isoformat(),
                'last_seen': datetime.now().isoformat()
            }).execute()
            
            if response.data:
                # الحصول على ID الذي أنشأه Supabase تلقائياً
                new_user_id = str(response.data[0]['id'])
                
                # إنشاء كائن User وتسجيل الدخول
                user = User(
                    id=new_user_id,
                    username=username,
                    email=email,
                    password=generate_password_hash(password),
                    avatar='default.png',
                    theme='light'
                )
                
                login_user(user)
                
                # تحديث بيانات المستخدم المحلية
                users[new_user_id] = {
                    'username': username,
                    'email': email,
                    'password': generate_password_hash(password),
                    'avatar': 'default.png',
                    'theme': 'light',
                    'joined_at': datetime.now().isoformat(),
                    'last_seen': datetime.now().isoformat()
                }
                
                return redirect(url_for('dashboard'))
            else:
                return render_template('register.html', error='حدث خطأ أثناء إنشاء الحساب في قاعدة البيانات')
                
        except Exception as e:
            print(f"Error creating user: {e}")
            return render_template('register.html', error='حدث خطأ أثناء إنشاء الحساب')
    
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    users = load_users()
    rooms = load_rooms()
    messages = load_messages()
    
    # الحصول على آخر الرسائل من كل غرفة
    room_last_messages = {}
    for room_name, room_messages in messages.get('rooms', {}).items():
        if room_messages:
            last_msg = room_messages[-1]
            room_last_messages[room_name] = {
                'message': decrypt_message(last_msg['message'])[:50] + '...' if len(last_msg['message']) > 50 else decrypt_message(last_msg['message']),
                'username': last_msg['username'],
                'timestamp': last_msg['timestamp']
            }
    
    # الحصول على آخر الرسائل الخاصة
    private_last_messages = {}
    private_chats = messages.get('private', {})
    for chat_key, chat_messages in private_chats.items():
        if current_user.id in chat_key and chat_messages:
            last_msg = chat_messages[-1]
            other_user_id = chat_key.split('_')[0] if chat_key.split('_')[0] != current_user.id else chat_key.split('_')[1]
            other_user = users.get(other_user_id, {})
            private_last_messages[other_user_id] = {
                'username': other_user.get('username', 'Unknown'),
                'message': decrypt_message(last_msg['message'])[:50] + '...' if len(last_msg['message']) > 50 else decrypt_message(last_msg['message']),
                'timestamp': last_msg['timestamp']
            }
    
    return render_template('dashboard.html', 
                         username=current_user.username,
                         avatar=current_user.avatar,
                         rooms=rooms,
                         room_last_messages=room_last_messages,
                         private_last_messages=private_last_messages,
                         users=users)

@app.route('/chat/<room_name>')
@login_required
def chat_room(room_name):
    rooms = load_rooms()
    if room_name not in rooms:
        rooms[room_name] = {
            'name': room_name,
            'created_by': current_user.id,
            'created_at': datetime.now().isoformat(),
            'description': f'غرفة دردشة {room_name}'
        }
        save_rooms(rooms)
    
    messages_data = load_messages()
    if room_name not in messages_data['rooms']:
        messages_data['rooms'][room_name] = []
        save_messages(messages_data)
    
    room_messages = messages_data['rooms'][room_name][-100:]  # آخر 100 رسالة
    for msg in room_messages:
        msg['message'] = decrypt_message(msg['message'])
    
    return render_template('chat_room.html', 
                         room_name=room_name,
                         username=current_user.username,
                         avatar=current_user.avatar,
                         messages=room_messages,
                         room_info=rooms[room_name])

@app.route('/private/<user_id>')
@login_required
def private_chat(user_id):
    users = load_users()
    if user_id not in users:
        return redirect(url_for('dashboard'))
    
    # إنشاء مفتاح محادثة فريد
    chat_key = '_'.join(sorted([current_user.id, user_id]))
    
    messages_data = load_messages()
    if chat_key not in messages_data['private']:
        messages_data['private'][chat_key] = []
        save_messages(messages_data)
    
    private_messages = messages_data['private'][chat_key][-100:]  # آخر 100 رسالة
    for msg in private_messages:
        msg['message'] = decrypt_message(msg['message'])
    
    return render_template('private_chat.html', 
                         other_user=users[user_id],
                         username=current_user.username,
                         avatar=current_user.avatar,
                         messages=private_messages,
                         chat_key=chat_key)

@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '')
    if not query:
        return render_template('search_results.html', results=[], query=query)
    
    users_data = load_users()
    messages_data = load_messages()
    results = []
    
    # البحث في المستخدمين
    for user_id, user_data in users_data.items():
        if query.lower() in user_data['username'].lower() and user_id != current_user.id:
            results.append({
                'type': 'user',
                'id': user_id,
                'name': user_data['username'],
                'avatar': user_data.get('avatar', 'default.png')
            })
    
    # البحث في الغرف
    rooms_data = load_rooms()
    for room_name, room_data in rooms_data.items():
        if query.lower() in room_name.lower():
            results.append({
                'type': 'room',
                'id': room_name,
                'name': room_name,
                'description': room_data.get('description', '')
            })
    
    # البحث في الرسائل (في الغرف التي يشارك فيها المستخدم)
    for room_name, messages in messages_data.get('rooms', {}).items():
        if room_name in rooms_data:  # فقط الغرف الموجودة
            for msg in messages:
                if query.lower() in decrypt_message(msg['message']).lower():
                    results.append({
                        'type': 'message',
                        'room': room_name,
                        'username': msg['username'],
                        'message': decrypt_message(msg['message']),
                        'timestamp': msg['timestamp']
                    })
    
    return render_template('search_results.html', results=results, query=query)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    users = load_users()
    if request.method == 'POST':
        username = request.form.get('username')
        avatar = request.files.get('avatar')
        
        if username and username != current_user.username:
            # التحقق من أن اسم المستخدم غير مأخوذ
            for user_id, user_data in users.items():
                if user_data['username'] == username and user_id != current_user.id:
                    return render_template('profile.html', error='اسم المستخدم مسجل مسبقاً')
            
            users[current_user.id]['username'] = username
        
        if avatar:
            filename = f"user_{current_user.id}_{int(datetime.now().timestamp())}.png"
            avatar_path = os.path.join(app.root_path, 'static', 'img', 'avatars', filename)
            try:
                avatar.save(avatar_path)
                users[current_user.id]['avatar'] = filename
            except Exception as e:
                logging.error(f"Error saving avatar: {e}")
                return render_template('profile.html', error='حدث خطأ أثناء حفظ الصورة')
        if save_users(users):
            return redirect(url_for('profile', success=True))
        else:
            return render_template('profile.html', error='حدث خطأ أثناء حفظ التغييرات')
    
    return render_template('profile.html', 
                         user=users.get(current_user.id, {}))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    users = load_users()
    if request.method == 'POST':
        theme = request.form.get('theme')
        notifications = request.form.get('notifications') == 'on'
        
        users[current_user.id]['theme'] = theme
        users[current_user.id]['notifications'] = notifications
        
        if save_users(users):
            return redirect(url_for('settings', success=True))
        else:
            return render_template('settings.html', error='حدث خطأ أثناء حفظ الإعدادات')
    
    return render_template('settings.html', 
                         user=users.get(current_user.id, {}))

@app.route('/logout')
@login_required
def logout():
    # تحديث وقت آخر زيارة
    users = load_users()
    if current_user.id in users:
        users[current_user.id]['last_seen'] = datetime.now().isoformat()
        save_users(users)
    
    logout_user()
    return redirect(url_for('index'))

# Routes for static files
@app.route('/static/img/avatars/<filename>')
def serve_avatar(filename):
    return send_from_directory(os.path.join(app.root_path, 'static', 'img', 'avatars'), filename)

@app.route('/api/rooms', methods=['GET'])
@login_required
def get_rooms():
    user_rooms = get_user_rooms(current_user.id)
    return jsonify([{
        'id': room.id,
        'name': room.name,
        'description': room.description,
        'unread_count': get_unread_count(room.id, current_user.id)
    } for room in user_rooms])

@app.route('/api/rooms', methods=['POST'])
@login_required
def create_new_room():
    data = request.get_json()
    room = create_room(
        name=data['name'],
        description=data.get('description', ''),
        created_by=current_user.id,
        is_public=data.get('is_public', True)
    )
    add_user_to_room(current_user.id, room.id)
    return jsonify({'id': room.id, 'name': room.name})

@app.route('/api/messages/<int:room_id>', methods=['GET'])
@login_required
def get_messages(room_id):
    messages = get_room_messages(room_id)
    return jsonify([{
        'id': msg.id,
        'user_id': msg.user_id,
        'username': msg.username,
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat(),
        'message_type': msg.message_type
    } for msg in messages])

@app.route('/api/messages', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    message = save_message(
        room_id=data['room_id'],
        user_id=current_user.id,
        username=current_user.username,
        content=data['content'],
        message_type=data.get('message_type', 'text'),
        is_private=data.get('is_private', False),
        recipient_id=data.get('recipient_id')
    )
    return jsonify({'id': message.id, 'timestamp': message.timestamp.isoformat()})

# في routes نستخدم النماذج مباشرة
@app.route('/api/users/<int:user_id>')
@login_required
def get_user_profile(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'username': user.username,
        'avatar_url': user.avatar_url,
        'is_online': user.is_online,
        'last_seen': user.last_seen.isoformat()
    })

@app.route('/api/rooms/<int:room_id>/messages')
@login_required
def get_room_messages_route(room_id):
    messages = Message.query.filter_by(room_id=room_id)\
        .order_by(Message.timestamp.desc())\
        .limit(100)\
        .all()
    
    return jsonify([{
        'id': msg.id,
        'user_id': msg.user_id,
        'username': msg.username,
        'content': msg.content,
        'timestamp': msg.timestamp.isoformat(),
        'message_type': msg.message_type
    } for msg in messages])
# أحداث SocketIO
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        emit('status', {'msg': f'{current_user.username} متصل الآن', 'username': 'System'})

@socketio.on('join_room')
def handle_join_room(data):
    room_id = data['room_id']
    join_room(f'room_{room_id}')
    update_user_online_status(current_user.id, True)

@socketio.on('leave_room')
def handle_leave_room(data):
    room_id = data['room_id']
    leave_room(f'room_{room_id}')
    update_user_online_status(current_user.id, False)

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        update_user_online_status(current_user.id, False)
@socketio.on('join')
@login_required_socket
def handle_join(data):
    room = data['room']
    join_room(room)
    emit('status', {
        'msg': f'{current_user.username} انضم إلى الغرفة',
        'username': 'System',
        'timestamp': datetime.now().isoformat()
    }, room=room)

@socketio.on('leave')
@login_required_socket
def handle_leave(data):
    room = data['room']
    leave_room(room)
    emit('status', {
        'msg': f'{current_user.username} غادر الغرفة',
        'username': 'System',
        'timestamp': datetime.now().isoformat()
    }, room=room)

@socketio.on('message')
@login_required_socket
def handle_message(data):
    room = data.get('room')
    message_text = data['message']
    is_private = data.get('private', False)
    recipient_id = data.get('recipient')
    
    # تشفير الرسالة قبل تخزينها
    encrypted_message = encrypt_message(message_text)
    
    message = {
        'username': current_user.username,
        'user_id': current_user.id,
        'message': encrypted_message,
        'timestamp': datetime.now().isoformat()
    }
    
    messages = load_messages()
    
    if is_private and recipient_id:
        # محادثة خاصة
        chat_key = '_'.join(sorted([current_user.id, recipient_id]))
        if chat_key not in messages['private']:
            messages['private'][chat_key] = []
        messages['private'][chat_key].append(message)
        save_messages(messages)
        
        # إرسال الرسالة إلى المستلم
        emit('private_message', {
            'username': current_user.username,
            'user_id': current_user.id,
            'message': message_text,  # الرسالة غير مشفرة للإرسال
            'timestamp': message['timestamp']
        }, room=chat_key)
    else:
        # غرفة دردشة عامة
        if room not in messages['rooms']:
            messages['rooms'][room] = []
        messages['rooms'][room].append(message)
        save_messages(messages)
        
        # إرسال الرسالة إلى جميع المشتركين في الغرفة
        emit('message', {
            'username': current_user.username,
            'user_id': current_user.id,
            'message': message_text,  # الرسالة غير مشفرة للإرسال
            'timestamp': message['timestamp']
        }, room=room)

@socketio.on('typing')
@login_required_socket
def handle_typing(data):
    room = data['room']
    is_private = data.get('private', False)
    
    if is_private:
        recipient_id = data.get('recipient')
        chat_key = '_'.join(sorted([current_user.id, recipient_id]))
        emit('typing', {
            'username': current_user.username,
            'is_typing': data['is_typing']
        }, room=chat_key, include_self=False)
    else:
        emit('typing', {
            'username': current_user.username,
            'is_typing': data['is_typing']
        }, room=room, include_self=False)

@socketio.on('user_activity')
@login_required_socket
def handle_user_activity(data):
    users = load_users()
    if current_user.id in users:
        users[current_user.id]['last_seen'] = datetime.now().isoformat()
        save_users(users)

if __name__ == '__main__':
    # إنشاء مجلدات البيانات إذا لم تكن موجودة
    os.makedirs(get_data_path(''), exist_ok=True)
    os.makedirs(get_data_path('backups'), exist_ok=True)
    
    # تحديد المنفذ بناءً على البيئة
    port = int(os.environ.get('PORT', 5000))
    
    # تشغيل التطبيق
    socketio.run(app, host='0.0.0.0', port=port, debug=os.environ.get('DEBUG', 'False').lower() == 'true')
