# utils.py - دوال مساعدة
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets
import string

def generate_password(length=12):
    """توليد كلمة مرور عشوائية"""
    characters = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(characters) for i in range(length))

def is_valid_email(email):
    """التحقق من صحة البريد الإلكتروني"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_valid_username(username):
    """التحقق من صحة اسم المستخدم"""
    import re
    pattern = r'^[a-zA-Z0-9_]{3,50}$'
    return re.match(pattern, username) is not None

def format_timestamp(timestamp):
    """تنسيق التاريخ للعرض"""
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff < timedelta(minutes=1):
        return 'الآن'
    elif diff < timedelta(hours=1):
        return f'منذ {diff.seconds // 60} دقيقة'
    elif diff < timedelta(days=1):
        return f'منذ {diff.seconds // 3600} ساعة'
    elif diff < timedelta(days=30):
        return f'منذ {diff.days} يوم'
    else:
        return timestamp.strftime('%Y-%m-%d %H:%M')