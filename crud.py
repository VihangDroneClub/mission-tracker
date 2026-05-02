from datetime import datetime, timezone
from database import supabase
import uuid
import json

def log_action(user_id: str, action: str, entity_type: str, entity_id: str,
               old_values: dict | None = None, new_values: dict | None = None):
    """Insert an audit log entry."""
    supabase.table("audit_logs").insert({
        "user_id": user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "old_values": json.dumps(old_values) if old_values else None,
        "new_values": json.dumps(new_values) if new_values else None,
    }).execute()

# ---------- Missions ----------
def get_all_missions():
    return supabase.table("missions").select("*").order("created_at", desc=False).execute().data

def get_mission(mission_id):
    return supabase.table("missions").select("*").eq("id", mission_id).single().execute().data

def create_mission(name: str, description: str | None, user_id: str):
    data = {"name": name, "description": description}
    res = supabase.table("missions").insert(data).execute().data[0]
    log_action(user_id, "mission_created", "mission", res["id"], new_values=data)
    return res

def update_mission(mission_id: str, name: str, description: str | None, user_id: str):
    old = get_mission(mission_id)
    new_data = {"name": name, "description": description}
    supabase.table("missions").update(new_data).eq("id", mission_id).execute()
    log_action(user_id, "mission_updated", "mission", mission_id, old_values=old, new_values=new_data)

def delete_mission(mission_id: str, user_id: str):
    old = get_mission(mission_id)
    supabase.table("missions").delete().eq("id", mission_id).execute()
    log_action(user_id, "mission_deleted", "mission", mission_id, old_values=old)

# ---------- Projects ----------
def get_projects_for_mission(mission_id: str):
    return supabase.table("projects").select("*").eq("mission_id", mission_id).order("created_at").execute().data

def get_project(project_id: str):
    return supabase.table("projects").select("*").eq("id", project_id).single().execute().data

def create_project(name: str, description: str | None, mission_id: str, user_id: str):
    data = {"name": name, "description": description, "mission_id": mission_id}
    res = supabase.table("projects").insert(data).execute().data[0]
    log_action(user_id, "project_created", "project", res["id"], new_values=data)
    return res

def update_project(project_id: str, name: str, description: str | None, user_id: str):
    old = get_project(project_id)
    new_data = {"name": name, "description": description}
    supabase.table("projects").update(new_data).eq("id", project_id).execute()
    log_action(user_id, "project_updated", "project", project_id, old_values=old, new_values=new_data)

def delete_project(project_id: str, user_id: str):
    old = get_project(project_id)
    supabase.table("projects").delete().eq("id", project_id).execute()
    log_action(user_id, "project_deleted", "project", project_id, old_values=old)

# ---------- Tasks ----------
def get_tasks_for_project(project_id: str):
    return supabase.table("tasks").select("*").eq("project_id", project_id).order("created_at").execute().data

def get_task(task_id: str):
    return supabase.table("tasks").select("*").eq("id", task_id).single().execute().data

def create_task(title: str, description: str | None, project_id: str, assignee_id: str | None, user_id: str):
    data = {
        "title": title,
        "description": description,
        "project_id": project_id,
        "assignee_id": assignee_id,
        "status": "todo"
    }
    res = supabase.table("tasks").insert(data).execute().data[0]
    log_action(user_id, "task_created", "task", res["id"], new_values=data)
    return res

def update_task_status(task_id: str, new_status: str, user_id: str):
    old = get_task(task_id)
    # Enforce valid transitions: todo -> in_progress -> done (no backward)
    if old["status"] == "done":
        raise Exception("Cannot change a completed task")
    if old["status"] == "todo" and new_status not in ("in_progress",):
        raise Exception("Can only move to In Progress")
    if old["status"] == "in_progress" and new_status not in ("done",):
        raise Exception("Can only move to Done")
    supabase.table("tasks").update({"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}).eq("id", task_id).execute()
    log_action(user_id, "task_status_changed", "task", task_id, old_values={"status": old["status"]}, new_values={"status": new_status})

def assign_task(task_id: str, assignee_id: str | None, user_id: str):
    old = get_task(task_id)
    supabase.table("tasks").update({"assignee_id": assignee_id}).eq("id", task_id).execute()
    log_action(user_id, "task_assigned", "task", task_id, old_values={"assignee_id": old["assignee_id"]}, new_values={"assignee_id": assignee_id})

# ---------- Users (for assignment dropdown) ----------
def get_all_users():
    """Returns all profiles (id, role) joined with auth.users email."""
    # We can't directly join auth.users via supabase-py? Use a raw SQL or just fetch profiles and then get emails via another query.
    # For simplicity, just return profiles. We'll later map to email in the route if needed.
    profiles = supabase.table("profiles").select("id, role").execute().data
    # Get emails from auth.users using admin API? That requires service_role key. Instead, we'll use the admin API if available.
    # We'll use a simple approach: for each profile, we'll get user by id using supabase.auth.admin.get_user_by_id (needs service_role).
    # Since we might not have service_role, we'll store email in profiles later. For now, we'll just show id and role.
    # Let's just return profiles and we'll display ID or add a note.
    return profiles
