import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Path to the .env file in the same directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

try:
    from supabase import create_client, Client
except ImportError:
    print("Error: 'supabase' library not found. Please install it with 'pip install supabase'.")
    sys.exit(1)

def create_advisor():
    url = os.environ.get("SUPABASE_URL")
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not service_role_key:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY missing from .env")
        return

    # Initialize admin client
    supabase_admin: Client = create_client(url, service_role_key)

    # --- CONFIGURATION ---
    # Change these values as needed
    CLUB_NAME = "VIHANG" 
    EMAIL = "advisor@example.com"
    PASSWORD = "TemporaryPassword123!"
    DISPLAY_NAME = "Faculty Advisor"
    # ---------------------

    print(f"Creating credentials for: {EMAIL}...")

    try:
        # 1. Get Organization ID
        org_res = supabase_admin.table("organizations").select("id").ilike("name", CLUB_NAME).execute()
        if not org_res.data:
            print(f"Error: Club '{CLUB_NAME}' not found in database.")
            return
        org_id = org_res.data[0]["id"]

        # 2. Create Auth User
        # Using admin API to bypass email confirmation
        auth_res = supabase_admin.auth.admin.create_user({
            "email": EMAIL,
            "password": PASSWORD,
            "email_confirm": True
        })
        user_id = auth_res.user.id
        print(f"User created in Auth successfully. ID: {user_id}")

        # 3. Create/Upsert Profile
        profile_data = {
            "id": user_id,
            "organization_id": org_id,
            "role": "lead",  # Leads can see everything but have fewer destructive permissions than admins
            "display_name": DISPLAY_NAME,
            "email": EMAIL
        }
        supabase_admin.table("profiles").upsert(profile_data).execute()
        
        print("\n" + "="*40)
        print("SUCCESS: Advisor Credentials Created")
        print("="*40)
        print(f"Club Identity: {CLUB_NAME}")
        print(f"Email:         {EMAIL}")
        print(f"Password:      {PASSWORD}")
        print("="*40)
        print("Your advisor can now log in at your deployment URL.")

    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    create_advisor()
