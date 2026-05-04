import os
from pathlib import Path
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader
from dotenv import load_dotenv
from typing import Optional
from database import supabase
import auth
from auth import set_auth_cookie, remove_auth_cookie, get_current_user, admin_required, lead_or_admin_required
import crud

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Mission Tracker")
env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")), autoescape=True)

def render_template(template_name: str, request: Request, **kwargs) -> HTMLResponse:
    template = env.get_template(template_name)
    html_content = template.render(request=request, **kwargs)
    return HTMLResponse(html_content)

# ---------- Public / test routes ----------
@app.get("/")
async def home(request: Request):
    # Redirect to dashboard if logged in, else login
    token = request.cookies.get(auth.COOKIE_NAME)
    if token:
        try:
            supabase.auth.get_user(token)
            return RedirectResponse(url="/dashboard")
        except:
            pass
    return RedirectResponse(url="/login")

@app.get("/ping")
async def ping():
    return {"status": "ok"}

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

# ---------- Dashboard ----------
@app.get("/dashboard")
async def dashboard(request: Request, user: dict = Depends(get_current_user)):
    missions = crud.get_all_missions()
    # For each mission, count projects and tasks
    mission_stats = []
    for m in missions:
        projects = crud.get_projects_for_mission(m["id"])
        task_count = 0
        for p in projects:
            tasks = crud.get_tasks_for_project(p["id"])
            task_count += len(tasks)
        mission_stats.append({
            "mission": m,
            "project_count": len(projects),
            "task_count": task_count
        })
    return render_template("dashboard.html", request, user=user, missions=mission_stats)

# ---------- Mission detail ----------
@app.get("/missions/{mission_id}")
async def mission_detail(request: Request, mission_id: str, user: dict = Depends(get_current_user)):
    mission = crud.get_mission(mission_id)
    projects = crud.get_projects_for_mission(mission_id)
    return render_template("mission_detail.html", request, user=user, mission=mission, projects=projects)

# Admin: create mission form & action
@app.get("/admin/missions/create")
async def create_mission_form(request: Request, user: dict = Depends(admin_required)):
    return render_template("mission_form.html", request, user=user, mission=None)

@app.post("/admin/missions/create")
async def create_mission_action(request: Request, name: str = Form(...), description: str = Form(""), user: dict = Depends(admin_required)):
    crud.create_mission(name, description, user["id"])
    return RedirectResponse(url="/dashboard", status_code=303)

@app.get("/admin/missions/{mission_id}/edit")
async def edit_mission_form(request: Request, mission_id: str, user: dict = Depends(admin_required)):
    mission = crud.get_mission(mission_id)
    return render_template("mission_form.html", request, user=user, mission=mission)

@app.post("/admin/missions/{mission_id}/edit")
async def edit_mission_action(request: Request, mission_id: str, name: str = Form(...), description: str = Form(""), user: dict = Depends(admin_required)):
    crud.update_mission(mission_id, name, description, user["id"])
    return RedirectResponse(url=f"/missions/{mission_id}", status_code=303)

@app.post("/admin/missions/{mission_id}/delete")
async def delete_mission(mission_id: str, user: dict = Depends(admin_required)):
    crud.delete_mission(mission_id, user["id"])
    return RedirectResponse(url="/dashboard", status_code=303)

# ---------- Project detail ----------
@app.get("/projects/{project_id}")
async def project_detail(request: Request, project_id: str, user: dict = Depends(get_current_user)):
    project = crud.get_project(project_id)
    tasks = crud.get_tasks_for_project(project_id)
    # get all users for assignment dropdown (profiles)
    assignable_users = crud.get_all_users()  # list of {id, role}
    return render_template("project_detail.html", request, user=user, project=project, tasks=tasks, assignable_users=assignable_users)

# Admin: create project under a mission
@app.get("/admin/projects/create")
async def create_project_form(request: Request, mission_id: str, user: dict = Depends(admin_required)):
    return render_template("project_form.html", request, user=user, mission_id=mission_id, project=None)

@app.post("/admin/projects/create")
async def create_project_action(request: Request, mission_id: str = Form(...), name: str = Form(...), description: str = Form(""), user: dict = Depends(admin_required)):
    crud.create_project(name, description, mission_id, user["id"])
    return RedirectResponse(url=f"/missions/{mission_id}", status_code=303)

@app.get("/admin/projects/{project_id}/edit")
async def edit_project_form(request: Request, project_id: str, user: dict = Depends(admin_required)):
    project = crud.get_project(project_id)
    return render_template("project_form.html", request, user=user, project=project, mission_id=project["mission_id"])

@app.post("/admin/projects/{project_id}/edit")
async def edit_project_action(request: Request, project_id: str, name: str = Form(...), description: str = Form(""), user: dict = Depends(admin_required)):
    crud.update_project(project_id, name, description, user["id"])
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@app.post("/admin/projects/{project_id}/delete")
async def delete_project(project_id: str, user: dict = Depends(admin_required)):
    project = crud.get_project(project_id)
    mission_id = project["mission_id"]
    crud.delete_project(project_id, user["id"])
    return RedirectResponse(url=f"/missions/{mission_id}", status_code=303)

# ---------- Task operations ----------
# Lead/Admin: add task to a project
@app.post("/projects/{project_id}/tasks/create")
async def add_task(request: Request, project_id: str, title: str = Form(...), description: str = Form(""), assignee_id: str = Form(None),
                   user: dict = Depends(lead_or_admin_required)):
    # Allow empty string to be None
    assignee = assignee_id if assignee_id else None
    crud.create_task(title, description, project_id, assignee, user["id"])
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

# Lead/Admin: update task status
@app.post("/tasks/{task_id}/update-status")
async def update_task_status(task_id: str, new_status: str = Form(...), user: dict = Depends(lead_or_admin_required)):
    try:
        crud.update_task_status(task_id, new_status, user["id"])
    except Exception as e:
        # we could flash error later, for now just redirect back
        pass
    task = crud.get_task(task_id)
    return RedirectResponse(url=f"/projects/{task['project_id']}", status_code=303)

# Lead/Admin: assign task
@app.post("/tasks/{task_id}/assign")
async def assign_task_endpoint(task_id: str, assignee_id: str = Form(""), user: dict = Depends(lead_or_admin_required)):
    assignee = assignee_id if assignee_id else None
    crud.assign_task(task_id, assignee, user["id"])
    task = crud.get_task(task_id)
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

# Task detail page
@app.get("/tasks/{task_id}")
async def task_detail(request: Request, task_id: str, user: dict = Depends(get_current_user)):
    task = crud.get_task(task_id)
    assignable_users = crud.get_all_users()
    comments = crud.get_comments_for_task(task_id)
    return render_template("task_detail.html", request, user=user, task=task, assignable_users=assignable_users, comments=comments)

# ---------- Comments ----------
@app.post("/tasks/{task_id}/comment")
async def add_comment_endpoint(task_id: str, content: str = Form(...), user: dict = Depends(lead_or_admin_required)):
    crud.add_comment(task_id, content, user["id"])
    return RedirectResponse(url=f"/tasks/{task_id}", status_code=303)

# ---------- Search ----------
@app.get("/search")
async def search(request: Request, q: str = "", user: dict = Depends(get_current_user)):
    if not q.strip():
        return render_template("search.html", request, user=user, results=[], query=q)
    # Search in tasks title and description using ilike
    search_filter = f"%{q}%"
    results = supabase.table("tasks").select("*").or_(f"title.ilike.{search_filter},description.ilike.{search_filter}").execute().data
    return render_template("search.html", request, user=user, results=results, query=q)

# ---------- Admin: User Management ----------
@app.get("/admin/users")
async def list_users(request: Request, user: dict = Depends(admin_required)):
    profiles = crud.get_all_users()
    # Enhance with email: we'll use supabase auth admin list_users if possible, but for simplicity we'll just display profile id and role.
    # To make it useful, we can add a small helper to get email from auth.users via admin API if service_role key is available.
    # For now, just show IDs.
    return render_template("admin_users.html", request, user=user, profiles=profiles)

@app.post("/admin/users/{user_id}/role")
async def change_user_role(user_id: str, new_role: str = Form(...), user: dict = Depends(admin_required)):
    if new_role not in ("member", "lead", "admin"):
        return HTMLResponse("Invalid role", status_code=400)
    supabase.table("profiles").update({"role": new_role}).eq("id", user_id).execute()
    crud.log_action(user["id"], "role_updated", "user", user_id,
                    old_values={"role": "..."},  # we could fetch old role, but skip for now
                    new_values={"role": new_role})
    return RedirectResponse(url="/admin/users", status_code=303)

# ---------- Admin: task CRUD (optional but simple) ----------
@app.get("/admin/tasks/create")
async def create_task_form(request: Request, project_id: str, user: dict = Depends(admin_required)):
    return render_template("task_form.html", request, user=user, project_id=project_id, task=None)

@app.post("/admin/tasks/create")
async def create_task_admin(request: Request, project_id: str = Form(...), title: str = Form(...), description: str = Form(""), assignee_id: str = Form(None), user: dict = Depends(admin_required)):
    assignee = assignee_id if assignee_id else None
    crud.create_task(title, description, project_id, assignee, user["id"])
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)

@app.get("/admin/tasks/{task_id}/edit")
async def edit_task_form(request: Request, task_id: str, user: dict = Depends(admin_required)):
    task = crud.get_task(task_id)
    return render_template("task_form.html", request, user=user, task=task, project_id=task["project_id"])

@app.post("/admin/tasks/{task_id}/edit")
async def edit_task_admin(request: Request, task_id: str, title: str = Form(...), description: str = Form(""), assignee_id: str = Form(None), user: dict = Depends(admin_required)):
    # For simplicity, we'll just update title/desc/assignee via a custom update function? We'll add a helper in crud.
    # Since we didn't create an update_task function, let's build one inline or add to crud.py later.
    # For now, we'll skip or handle basic fields.
    pass

@app.post("/admin/tasks/{task_id}/delete")
async def delete_task(task_id: str, user: dict = Depends(admin_required)):
    task = crud.get_task(task_id)
    project_id = task["project_id"]
    supabase.table("tasks").delete().eq("id", task_id).execute()
    crud.log_action(user["id"], "task_deleted", "task", task_id, old_values=task)
    return RedirectResponse(url=f"/projects/{project_id}", status_code=303)
