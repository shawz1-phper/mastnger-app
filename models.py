from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.BigInteger, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    avatar_url = db.Column(db.String(255), default='default.png')
    theme = db.Column(db.String(20), default='light')
    is_online = db.Column(db.Boolean, default=False)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    messages = db.relationship('Message', backref='author', lazy=True)
    created_rooms = db.relationship('Room', backref='creator', lazy=True)
    room_memberships = db.relationship('UserRoom', backref='user', lazy=True)

class Room(db.Model):
    __tablename__ = 'rooms'
    
    id = db.Column(db.BigInteger, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.BigInteger, db.ForeignKey('users.id'))
    is_public = db.Column(db.Boolean, default=True)
    max_users = db.Column(db.Integer, default=100)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # العلاقات
    messages = db.relationship('Message', backref='room', lazy=True)
    members = db.relationship('UserRoom', backref='room', lazy=True)

class UserRoom(db.Model):
    __tablename__ = 'user_rooms'
    
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), primary_key=True)
    room_id = db.Column(db.BigInteger, db.ForeignKey('rooms.id'), primary_key=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_read = db.Column(db.DateTime, default=datetime.utcnow)

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.BigInteger, primary_key=True)
    room_id = db.Column(db.BigInteger, db.ForeignKey('rooms.id'))
    user_id = db.Column(db.BigInteger, db.ForeignKey('users.id'), nullable=False)
    username = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), default='text')
    is_private = db.Column(db.Boolean, default=False)
    recipient_id = db.Column(db.BigInteger, db.ForeignKey('users.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # العلاقات
    recipient = db.relationship('User', foreign_keys=[recipient_id])