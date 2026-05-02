import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
from database import supabase

# Load environment variables from .env
load_dotenv()

# Project root (where main.py lives)
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="Mission Tracker")

# Set up Jinja2 environment manually (no Starlette wrapper)
env = Environment(
    loader=FileSystemLoader(str(BASE_DIR / "templates")),
    autoescape=True,
)

@app.get("/")
async def home(request: Request):
    # Get the template, render it, and return an HTMLResponse
    template = env.get_template("base.html")
    html_content = template.render(request=request, title="Mission Tracker")
    return HTMLResponse(html_content)

@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "FastAPI is running!"}

@app.get("/missions/json")
async def missions_json():
    """Temporary test route – fetch missions from Supabase."""
    response = supabase.table("missions").select("*").execute()
    return response.data
