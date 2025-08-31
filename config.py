import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SOCKETIO_ASYNC_MODE = 'threading'
    
    # إعدادات قاعدة البيانات (للمستقبل)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True
    SERVER_NAME = 'localhost:5000'
    PREFERRED_URL_SCHEME = 'http'

class ProductionConfig(Config):
    DEBUG = False
    PREFERRED_URL_SCHEME = 'https'

# اختيار التهيئة بناءً على البيئة
if os.environ.get('FLASK_ENV') == 'production' or os.environ.get('RENDER'):
    config = ProductionConfig()
else:
    config = DevelopmentConfig()
