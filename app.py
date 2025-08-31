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
try:
    import eventlet
    print("Eventlet imported successfully")
except ImportError as e:
    print(f"Eventlet import error: {e}")
# تحميل متغيرات البيئة
load_dotenv()

# تهيئة التطبيق
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-'+secrets.token_hex(16))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
app.config['SOCKETIO_ASYNC_MODE'] = 'gevent'
socketio = SocketIO(app, async_mode='gevent')
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

# تحميل بيانات المستخدمين
def load_users():
    return load_json_data('users.json', {})

def save_users(users):
    create_backup('users.json')
    return save_json_data('users.json', users)

def load_messages():
    return load_json_data('messages.json', {"rooms": {}, "private": {}})

def save_messages(messages):
    create_backup('messages.json')
    return save_json_data('messages.json', messages)

def load_rooms():
    return load_json_data('rooms.json', {})

def save_rooms(rooms):
    create_backup('rooms.json')
    return save_json_data('rooms.json', rooms)

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
        for user_data in users.values():
            if user_data['email'] == email:
                return render_template('register.html', error='البريد الإلكتروني مسجل مسبقاً')
            if user_data['username'] == username:
                return render_template('register.html', error='اسم المستخدم مسجل مسبقاً')
        
        # إنشاء مستخدم جديد
        user_id = str(len(users) + 1)
        users[user_id] = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'avatar': 'default.png',
            'theme': 'light',
            'joined_at': datetime.now().isoformat(),
            'last_seen': datetime.now().isoformat()
        }
        
        if save_users(users):
            user = User(user_id, username, email, users[user_id]['password'])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
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
            avatar.save(avatar_path)
            users[current_user.id]['avatar'] = filename
        
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

# أحداث SocketIO
@socketio.on('connect')
def handle_connect():
    if current_user.is_authenticated:
        emit('status', {'msg': f'{current_user.username} متصل الآن', 'username': 'System'})

@socketio.on('disconnect')
def handle_disconnect():
    if current_user.is_authenticated:
        emit('status', {'msg': f'{current_user.username} غير متصل الآن', 'username': 'System'})

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
