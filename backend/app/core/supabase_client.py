from supabase import create_client, Client
from app.core.config import settings

def get_supabase() -> Client:
    # Ensure URL and key are provided
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise ValueError("Supabase URL and Service Key must be set in environment")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
