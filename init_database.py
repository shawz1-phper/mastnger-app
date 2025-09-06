#!/usr/bin/env python3
"""
init_database.py - إنشاء الجداول والسياسات في Supabase
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv
import time

# تحميل environment variables
load_dotenv()

def init_supabase():
    """تهيئة عميل Supabase"""
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')
    
    if not supabase_url or not supabase_key:
        raise ValueError("❌ SUPABASE_URL and SUPABASE_KEY must be set in environment variables")
    
    return create_client(supabase_url, supabase_key)

def create_tables(supabase: Client):
    """إنشاء الجداول في Supabase"""
    
    print("🗃️ Creating tables...")
    
    # 1. جدول المستخدمين
    users_table = """
    CREATE TABLE IF NOT EXISTS users (
        id BIGSERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        avatar_url VARCHAR(255) DEFAULT 'default.png',
        theme VARCHAR(20) DEFAULT 'light',
        is_online BOOLEAN DEFAULT FALSE,
        last_seen TIMESTAMPTZ DEFAULT NOW(),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        
        CONSTRAINT valid_username CHECK (username ~ '^[a-zA-Z0-9_]{3,50}$'),
        CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$')
    );
    """
    
    # 2. جدول الغرف
    rooms_table = """
    CREATE TABLE IF NOT EXISTS rooms (
        id BIGSERIAL PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        description TEXT,
        created_by BIGINT REFERENCES users(id),
        is_public BOOLEAN DEFAULT TRUE,
        max_users INTEGER DEFAULT 100,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        
        CONSTRAINT valid_room_name CHECK (length(name) BETWEEN 3 AND 100)
    );
    """
    
    # 3. جدول علاقة المستخدمين بالغرف
    user_rooms_table = """
    CREATE TABLE IF NOT EXISTS user_rooms (
        user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
        room_id BIGINT REFERENCES rooms(id) ON DELETE CASCADE,
        joined_at TIMESTAMPTZ DEFAULT NOW(),
        last_read TIMESTAMPTZ DEFAULT NOW(),
        
        PRIMARY KEY (user_id, room_id)
    );
    """
    
    # 4. جدول الرسائل
    messages_table = """
    CREATE TABLE IF NOT EXISTS messages (
        id BIGSERIAL PRIMARY KEY,
        room_id BIGINT REFERENCES rooms(id) ON DELETE CASCADE,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        username VARCHAR(50) NOT NULL,
        content TEXT NOT NULL,
        message_type VARCHAR(20) DEFAULT 'text',
        is_private BOOLEAN DEFAULT FALSE,
        recipient_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
        timestamp TIMESTAMPTZ DEFAULT NOW(),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        
        CONSTRAINT non_empty_content CHECK (length(content) > 0),
        CONSTRAINT valid_message_type CHECK (message_type IN ('text', 'image', 'file', 'system'))
    );
    """
    
    tables = [
        users_table, rooms_table, user_rooms_table, messages_table
    ]
    
    for i, table_query in enumerate(tables, 1):
        try:
            result = supabase.rpc('exec_sql', {'query': table_query}).execute()
            print(f"✅ Table {i} created successfully")
            time.sleep(1)  # تجنب rate limiting
        except Exception as e:
            print(f"❌ Error creating table {i}: {e}")

def create_indexes(supabase: Client):
    """إنشاء indexes لتحسين الأداء"""
    
    print("📊 Creating indexes...")
    
    indexes = [
        # indexes للمستخدمين
        "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);",
        "CREATE INDEX IF NOT EXISTS idx_users_online ON users(is_online);",
        "CREATE INDEX IF NOT EXISTS idx_users_last_seen ON users(last_seen DESC);",
        
        # indexes للغرف
        "CREATE INDEX IF NOT EXISTS idx_rooms_name ON rooms(name);",
        "CREATE INDEX IF NOT EXISTS idx_rooms_public ON rooms(is_public);",
        
        # indexes للعلاقات
        "CREATE INDEX IF NOT EXISTS idx_user_rooms_user ON user_rooms(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_user_rooms_room ON user_rooms(room_id);",
        
        # indexes للرسائل
        "CREATE INDEX IF NOT EXISTS idx_messages_room ON messages(room_id);",
        "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp DESC);",
        "CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_messages_private ON messages(is_private, user_id, recipient_id);",
        "CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id);"
    ]
    
    for i, index_query in enumerate(indexes, 1):
        try:
            result = supabase.rpc('exec_sql', {'query': index_query}).execute()
            print(f"✅ Index {i} created successfully")
            time.sleep(0.5)
        except Exception as e:
            print(f"⚠️  Error creating index {i}: {e}")

def enable_realtime(supabase: Client):
    """تمكين Realtime للجداول"""
    
    print("🔔 Enabling realtime...")
    
    realtime_tables = [
        "ALTER TABLE users REPLICA IDENTITY FULL;",
        "ALTER TABLE rooms REPLICA IDENTITY FULL;",
        "ALTER TABLE messages REPLICA IDENTITY FULL;",
        "ALTER TABLE user_rooms REPLICA IDENTITY FULL;"
    ]
    
    for query in realtime_tables:
        try:
            result = supabase.rpc('exec_sql', {'query': query}).execute()
            print("✅ Realtime enabled for tables")
            time.sleep(1)
        except Exception as e:
            print(f"❌ Error enabling realtime: {e}")

def create_policies(supabase: Client):
    """إنشاء policies للوصول الآمن"""
    
    print("🔒 Creating security policies...")
    
    # سياسات المستخدمين
    user_policies = [
        # سياسات القراءة
        """
        CREATE POLICY "Users can view all profiles" ON users
        FOR SELECT USING (true);
        """,
        
        # سياسات الإدخال
        """
        CREATE POLICY "Anyone can create a profile" ON users
        FOR INSERT WITH CHECK (true);
        """,
        
        # سياسات التحديث
        """
        CREATE POLICY "Users can update their own profile" ON users
        FOR UPDATE USING (auth.uid()::text = id::text);
        """
    ]
    
    # سياسات الغرف
    room_policies = [
        """
        CREATE POLICY "Anyone can view public rooms" ON rooms
        FOR SELECT USING (is_public = true);
        """,
        
        """
        CREATE POLICY "Users can view their private rooms" ON rooms
        FOR SELECT USING (
            is_public = false AND 
            EXISTS (
                SELECT 1 FROM user_rooms 
                WHERE user_rooms.room_id = rooms.id 
                AND user_rooms.user_id = auth.uid()::bigint
            )
        );
        """,
        
        """
        CREATE POLICY "Users can create rooms" ON rooms
        FOR INSERT WITH CHECK (auth.uid()::bigint = created_by);
        """,
        
        """
        CREATE POLICY "Room creators can update their rooms" ON rooms
        FOR UPDATE USING (auth.uid()::bigint = created_by);
        """
    ]
    
    # سياسات الرسائل
    message_policies = [
        """
        CREATE POLICY "Users can view room messages" ON messages
        FOR SELECT USING (
            NOT is_private AND 
            EXISTS (
                SELECT 1 FROM user_rooms 
                WHERE user_rooms.room_id = messages.room_id 
                AND user_rooms.user_id = auth.uid()::bigint
            )
        );
        """,
        
        """
        CREATE POLICY "Users can view private messages" ON messages
        FOR SELECT USING (
            is_private AND 
            (user_id = auth.uid()::bigint OR recipient_id = auth.uid()::bigint)
        );
        """,
        
        """
        CREATE POLICY "Users can send messages" ON messages
        FOR INSERT WITH CHECK (user_id = auth.uid()::bigint);
        """,
        
        """
        CREATE POLICY "Users can delete their own messages" ON messages
        FOR DELETE USING (user_id = auth.uid()::bigint);
        """
    ]
    
    # سياسات user_rooms
    user_rooms_policies = [
        """
        CREATE POLICY "Users can view their room memberships" ON user_rooms
        FOR SELECT USING (user_id = auth.uid()::bigint);
        """,
        
        """
        CREATE POLICY "Users can join rooms" ON user_rooms
        FOR INSERT WITH CHECK (user_id = auth.uid()::bigint);
        """,
        
        """
        CREATE POLICY "Users can leave rooms" ON user_rooms
        FOR DELETE USING (user_id = auth.uid()::bigint);
        """
    ]
    
    all_policies = user_policies + room_policies + message_policies + user_rooms_policies
    
    for i, policy_query in enumerate(all_policies, 1):
        try:
            result = supabase.rpc('exec_sql', {'query': policy_query}).execute()
            print(f"✅ Policy {i} created successfully")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️  Error creating policy {i}: {e}")

def test_connection(supabase: Client):
    """اختبار الاتصال والتحقق من الجداول"""
    
    print("🧪 Testing connection...")
    
    try:
        # اختبار استعلام بسيط
        result = supabase.table('users').select('count').execute()
        print("✅ Database connection successful")
        
        # التحقق من الجداول
        tables = ['users', 'rooms', 'messages', 'user_rooms']
        for table in tables:
            try:
                supabase.table(table).select('count', count='exact').limit(1).execute()
                print(f"✅ Table '{table}' exists and accessible")
            except:
                print(f"❌ Table '{table}' not accessible")
                
    except Exception as e:
        print(f"❌ Connection test failed: {e}")

def main():
    """الدالة الرئيسية"""
    
    print("🚀 Starting database initialization...")
    print("=" * 50)
    
    try:
        # تهيئة Supabase
        supabase = init_supabase()
        print("✅ Supabase client initialized")
        
        # إنشاء الجداول
        create_tables(supabase)
        
        # إنشاء indexes
        create_indexes(supabase)
        
        # تمكين realtime
        enable_realtime(supabase)
        
        # إنشاء policies
        create_policies(supabase)
        
        # اختبار الاتصال
        test_connection(supabase)
        
        print("=" * 50)
        print("🎉 Database initialization completed successfully!")
        print("📋 Next steps:")
        print("   1. Add your SUPABASE_URL and SUPABASE_KEY to .env")
        print("   2. Run: python init_database.py")
        print("   3. Start your Flask app: python app.py")
        
    except Exception as e:
        print(f"💥 Initialization failed: {e}")
        print("Please check your Supabase credentials and connection")

if __name__ == "__main__":
    main()