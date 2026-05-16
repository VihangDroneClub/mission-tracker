from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from typing import Optional
from database import supabase, supabase_admin
import auth
from auth import set_auth_cookie, remove_auth_cookie, get_current_user
from templates_utils import render_template

router = APIRouter(tags=["auth"])

@router.get("/request-access")
async def request_access_page(request: Request):
    return render_template("request_access.html", request)

@router.post("/request-access")
async def request_access_post(request: Request, full_name: str = Form(...), email: str = Form(...), club_name: str = Form(...), reason: str = Form(None)):
    try:
        payload = {
            "full_name": full_name,
            "email": email,
            "club_name": club_name,
            "reason": reason
        }
        # Use supabase_admin to bypass RLS for incoming requests
        client = supabase_admin if supabase_admin else supabase
        client.table("access_requests").insert(payload).execute()
        return render_template("request_access.html", request, message="Your request has been submitted. We will contact you shortly.")
    except Exception as e:
        return render_template("request_access.html", request, error=str(e))

@router.get("/login")
async def login_page(request: Request, message: Optional[str] = None):
    return render_template("login.html", request, message=message)

@router.post("/login")
async def login_post(request: Request, club_name: str = Form(...), email: str = Form(...), password: str = Form(...)):
    try:
        # 1. Authenticate
        auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        access_token = auth_response.session.access_token
        user_id = auth_response.user.id

        # 2. Verify Club Identity
        # We fetch the profile and join with organization
        profile_res = supabase.table("profiles").select("*, organizations(name)").eq("id", user_id).single().execute()
        if not profile_res.data:
            raise Exception("Profile not found")
        
        user_org_name = profile_res.data.get("organizations", {}).get("name", "")
        if user_org_name.lower() != club_name.lower():
            supabase.auth.sign_out()
            raise Exception(f"You do not belong to the club '{club_name}'")

        # 3. Success
        response = RedirectResponse(url="/dashboard", status_code=303)
        set_auth_cookie(response, access_token)
        return response
    except Exception as e:
        return render_template("login.html", request, error=str(e))

@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    remove_auth_cookie(response)
    return response

@router.get("/change-password")
async def change_password_page(request: Request, user: dict = Depends(get_current_user)):
    return render_template("change_password.html", request, user=user)

@router.post("/change-password")
async def change_password_post(request: Request, password: str = Form(...), confirm_password: str = Form(...), user: dict = Depends(get_current_user)):
    if password != confirm_password:
        return render_template("change_password.html", request, user=user, error="Passwords do not match")
    
    if len(password) < 6:
        return render_template("change_password.html", request, user=user, error="Password must be at least 6 characters")
    
    try:
        # Get the access token from cookies
        token = request.cookies.get(auth.COOKIE_NAME)
        # We need to set the session for the client to update the user
        supabase.postgrest.headers["Authorization"] = f"Bearer {token}"
        supabase.auth.set_session(token, "") # Refresh token not needed for just updating password usually
        
        supabase.auth.update_user({"password": password})
        return render_template("change_password.html", request, user=user, message="Password updated successfully")
    except Exception as e:
        return render_template("change_password.html", request, user=user, error=str(e))

@router.get("/forgot-password")
async def forgot_password_page(request: Request):
    return render_template("login.html", request, message="Please contact your Club administrator to reset your password. Native password reset is coming in v2.1.")
