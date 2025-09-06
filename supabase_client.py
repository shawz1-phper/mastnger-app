import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseClient:
    def __init__(self):
        self.url = os.environ.get('SUPABASE_URL')
        self.key = os.environ.get('SUPABASE_KEY')
        self.client: Client = create_client(self.url, self.key)
    
    def get_client(self):
        return self.client

# إنشاء instance global
supabase = SupabaseClient()