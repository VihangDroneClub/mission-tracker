import os
from pathlib import Path
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
from typing import Optional
from database import supabase
import auth
from auth import set_auth_cookie, remove_auth_cookie, get_current_user

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Mission Tracker")
env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")), autoescape=True)

# ---------- Helper to render templates as HTML ----------
def render_template(template_name: str, request: Request, **kwargs) -> HTMLResponse:
    template = env.get_template(template_name)
    html_content = template.render(request=request, **kwargs)
    return HTMLResponse(html_content)

# ---------- Public / test routes ----------
@app.get("/")
async def home(request: Request):
    return render_template("base.html", request, title="Mission Tracker")

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "FastAPI is running!"}

# ---------- Auth routes ----------
@app.get("/signup")
async def signup_page(request: Request):
    return render_template("signup.html", request)

@app.post("/signup")
async def signup_post(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        supabase.auth.sign_up({"email": email, "password": password})
    except Exception as e:
        return render_template("signup.html", request, error=str(e))
    return RedirectResponse(url="/login?message=Account created. Please log in.", status_code=303)

@app.get("/login")
async def login_page(request: Request, message: Optional[str] = None):
    return render_template("login.html", request, message=message)

@app.post("/login")
async def login_post(request: Request, email: str = Form(...), password: str = Form(...)):
    try:
        auth_response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        access_token = auth_response.session.access_token
        response = RedirectResponse(url="/dashboard", status_code=303)
        set_auth_cookie(response, access_token)
        return response
    except Exception as e:
        return render_template("login.html", request, error=str(e))

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login")
    remove_auth_cookie(response)
    return response

# ---------- Protected routes ----------
@app.get("/dashboard")
async def dashboard(request: Request, user: dict = Depends(get_current_user)):
    html = f"<h1>Welcome, {user['email']} (role: {user['role']})</h1><a href='/logout'>Logout</a>"
    return HTMLResponse(html)

@app.get("/missions/json")
async def missions_json(request: Request, user: dict = Depends(get_current_user)):
    response = supabase.table("missions").select("*").execute()
    return response.data
