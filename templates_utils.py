from fastapi import Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import date
import crud

BASE_DIR = Path(__file__).resolve().parent
env = Environment(loader=FileSystemLoader(str(BASE_DIR / "templates")), autoescape=True)

# Terminology Dictionaries
TACTICAL_DICT = {
    "dashboard": "Command Center",
    "tasks": "Directives",
    "todo": "AWAITING_EXEC",
    "in_progress": "ACTIVE_OP",
    "done": "OBJECTIVE_MET",
    "users": "Personnel Database",
    "audit_log": "System Records",
    "search": "Database Query",
    "analytics": "Telemetry Data",
    "mission": "Mission Operation",
    "project": "Node Cluster",
    "task": "Directive Unit",
    "overdue": "STALE_TASK",
    "due_today": "URGENT_SYNC",
    "due_this_week": "UPCOMING_OPS",
    "upcoming": "PLANNED_TRAJECTORY",
    "no_due": "ASYNC_UNSET",
    "priority": "THREAT_LEVEL",
    "status": "OPERATIONAL_STATUS",
    "lead": "Commanding_Officer",
    "member": "Pilot_Operative",
    "admin": "System_Admin"
}

STANDARD_DICT = {
    "dashboard": "Dashboard",
    "tasks": "Tasks",
    "todo": "To Do",
    "in_progress": "In Progress",
    "done": "Completed",
    "users": "User Management",
    "audit_log": "Audit Log",
    "search": "Search Engine",
    "analytics": "Analytics",
    "mission": "Mission",
    "project": "Project",
    "task": "Task",
    "overdue": "Overdue",
    "due_today": "Due Today",
    "due_this_week": "Due This Week",
    "upcoming": "Upcoming",
    "no_due": "No Due Date",
    "priority": "Priority",
    "status": "Status",
    "lead": "Project Lead",
    "member": "Member",
    "admin": "Administrator"
}

def get_username_map(org_id: str = None):
    try:
        users = crud.get_all_users_detailed(org_id)
        return {u["id"]: u["display_name"] or u["username"] or "Member" for u in users}
    except Exception as e:
        print(f"DEBUG: get_username_map failed: {e}")
        return {}

def render_template(template_name: str, request: Request, **kwargs) -> HTMLResponse:
    template = env.get_template(template_name)
    
    # Read preferences from cookies
    theme = request.cookies.get("theme", "dark")
    ui_mode = request.cookies.get("ui_mode", "tactical")
    
    # Select dictionary
    t_dict = TACTICAL_DICT if ui_mode == "tactical" else STANDARD_DICT
    
    if "username_map" not in kwargs:
        user = kwargs.get("user")
        org_id = user.get("organization_id") if user else None
        kwargs["username_map"] = get_username_map(org_id)
    
    html_content = template.render(
        request=request, 
        today=date.today(), 
        theme=theme,
        ui_mode=ui_mode,
        t=t_dict,
        **kwargs
    )
    return HTMLResponse(html_content)
