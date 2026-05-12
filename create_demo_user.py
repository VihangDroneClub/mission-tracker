import os
import sys
from database import supabase_admin, supabase

def create_user(email, password, club_name):
    print(f"Attempting to create user: {email}")
    
    if not supabase_admin:
        print("ERROR: SUPABASE_SERVICE_ROLE_KEY is not set. Cannot create user via admin API.")
        return

    try:
        # 1. Check if organization exists
        org_res = supabase.table("organizations").select("*").ilike("name", club_name).execute()
        if not org_res.data:
            print(f"Creating organization: {club_name}")
            org_res = supabase.table("organizations").insert({"name": club_name}).execute()
        
        org_id = org_res.data[0]["id"]

        # 2. Create the user in Auth
        auth_res = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": password,
            "email_confirm": True
        })
        user_id = auth_res.user.id
        print(f"Auth user created with ID: {user_id}")

        # 3. Create/Update Profile
        profile_data = {
            "id": user_id,
            "email": email,
            "organization_id": org_id,
            "role": "admin",
            "username": f"demo_{user_id[:5]}"
        }
        
        # Use supabase_admin for profile to bypass RLS
        supabase_admin.table("profiles").upsert(profile_data).execute()
        print(f"Profile created and linked to club: {club_name}")
        print("\nSUCCESS! You can now log in to the website.")

    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 create_demo_user.py <email> <password> <club_name>")
    else:
        create_user(sys.argv[1], sys.argv[2], sys.argv[3])
