import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-' + os.urandom(16).hex())
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SOCKETIO_ASYNC_MODE = 'threading'
    
    # إعدادات Supabase
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')
    SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY', '')
    
    # إعدادات قاعدة البيانات الذكية
    if os.environ.get('SUPABASE_URL') and os.environ.get('USE_SUPABASE', 'false').lower() == 'true':
        # استخدام Supabase PostgreSQL
        SQLALCHEMY_DATABASE_URI = os.environ.get('SUPABASE_DB_URL', '').replace(
            'postgresql://', 'postgresql://'  #确保格式正确
        ) or f"postgresql://{os.environ.get('SUPABASE_DB_USER', '')}:{os.environ.get('SUPABASE_DB_PASSWORD', '')}@{os.environ.get('SUPABASE_DB_HOST', '')}:{os.environ.get('SUPABASE_DB_PORT', '5432')}/{os.environ.get('SUPABASE_DB_NAME', '')}"
    else:
        # استخدام SQLite المحلي للتطوير
        SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }
    
    # إعدادات التطبيق
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

class DevelopmentConfig(Config):
    DEBUG = True
    SERVER_NAME = 'localhost:5000'
    PREFERRED_URL_SCHEME = 'http'
    EXPLAIN_TEMPLATE_LOADING = False
    
    # Override database for development
    if not os.environ.get('SUPABASE_URL'):
        SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    
    # إعدادات التطوير
    TEMPLATES_AUTO_RELOAD = True
    SEND_FILE_MAX_AGE_DEFAULT = 0  # disable caching for development

class ProductionConfig(Config):
    DEBUG = False
    PREFERRED_URL_SCHEME = 'https'
    SERVER_NAME = os.environ.get('SERVER_NAME', None)
    
    # تأكد من استخدام Supabase في الإنتاج
    if not os.environ.get('SUPABASE_URL'):
        print("⚠️  Warning: SUPABASE_URL not set in production environment!")
    
    # إعدادات الأمان للإنتاج
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_HTTPONLY = True
    
    # إعدادات الأداء
    TEMPLATES_AUTO_RELOAD = False
    SEND_FILE_MAX_AGE_DEFAULT = 3600  # cache for 1 hour

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SERVER_NAME = 'localhost:5000'

# اختيار التهيئة بناءً على البيئة
env = os.environ.get('FLASK_ENV', 'development').lower()

if env == 'production' or os.environ.get('RENDER'):
    config = ProductionConfig()
    print("🚀 Production configuration loaded")
elif env == 'testing':
    config = TestingConfig()
    print("🧪 Testing configuration loaded")
else:
    config = DevelopmentConfig()
    print("💻 Development configuration loaded")

# التحقق من إعدادات قاعدة البيانات
if config.SQLALCHEMY_DATABASE_URI.startswith('sqlite'):
    print("💾 Using SQLite database")
elif config.SQLALCHEMY_DATABASE_URI.startswith('postgresql'):
    print("🐘 Using PostgreSQL database")
else:
    print("❓ Unknown database type")

# التحقق من إعدادات Supabase
if config.SUPABASE_URL and config.SUPABASE_KEY:
    print("☁️  Supabase integration enabled")
else:
    print("⚠️  Supabase integration disabled")