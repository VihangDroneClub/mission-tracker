from fastapi import Request, HTTPException, Depends
from fastapi.responses import RedirectResponse
from database import supabase
from typing import Optional

# Cookie name
COOKIE_NAME = "access_token"

def set_auth_cookie(response: RedirectResponse, access_token: str):
    """Set the access token in an HTTP‑only cookie."""
    response.set_cookie(
        key=COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=False,     # set to True in production (HTTPS)
        samesite="lax",
        max_age=60 * 60 * 24 * 7,  # 1 week
    )

def remove_auth_cookie(response: RedirectResponse):
    response.delete_cookie(COOKIE_NAME)

async def get_current_user(request: Request) -> dict:
    """Dependency that returns the current user's profile or raises 401."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Verify token with Supabase
    try:
        user_response = supabase.auth.get_user(token)
        user = user_response.user
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fetch the profile from our `profiles` table
    profile_response = supabase.table("profiles").select("*").eq("id", user.id).execute()
    if not profile_response.data:
        raise HTTPException(status_code=401, detail="Profile not found")

    profile = profile_response.data[0]
    # Attach email and role to the user object for convenience
    user_dict = {
        "id": user.id,
        "email": user.email,
        "role": profile["role"],
    }
    return user_dict
