# Mission‑Project‑Task Tracker — Architecture Document

## 1. Overview
A web application that tracks a three‑level work hierarchy:  
**Mission → Project → Task**

- **Missions** contain many Projects.  
- **Projects** contain many Tasks.  
- Tasks can be assigned to a **lead** or a **member** (but only leads/admins can mark them complete).  
- Activities are logged (audit log).  
- A monthly progress dashboard shows completion stats per mission/project and per assignee.

## 2. Roles & Permissions

| Role   | View | Create/Edit Missions/Projects | Add Task to Project | Assign Task to | Update Task Status (todo, in_progress, done) | Comment on Task | Manage Users (change roles) | View Audit Log |
|--------|------|-------------------------------|---------------------|----------------|----------------------------------------------|-----------------|-----------------------------|----------------|
| member | ✅   | ❌                            | ❌                  | ❌             | ❌                                           | ❌              | ❌                          | ❌             |
| lead   | ✅   | ❌                            | ✅                  | ✅ (can assign to any member or lead) | ✅ (mark done/in_progress, but only they own status change) | ✅ | ❌ | ❌ |
| admin  | ✅   | ✅                            | ✅                  | ✅             | ✅                                           | ✅              | ✅                          | ✅             |

**Important nuance:** A lead can assign a task to a **member** (or another lead), but the member **cannot** change its status. Only the lead who manages the project (or any admin) can mark a task as `in_progress` or `done`. Members are purely observers.

## 3. Tech Stack (Python‑only, single codebase)
- **Backend / Web framework:** FastAPI  
- **Server‑side templates:** Jinja2  
- **Database & Auth:** Supabase (PostgreSQL + built‑in email/password auth)  
- **Deployment:** Vercel (serverless function running the FastAPI app)  
- **Version control:** GitHub  

Everything runs on Vercel – the FastAPI app renders full HTML pages. No separate frontend framework.

## 4. Database Schema (Supabase PostgreSQL)

### 4.1 Profiles (extends `auth.users`)
```sql
create table public.profiles (
  id uuid references auth.users primary key,
  role text not null default 'member' check (role in ('member', 'lead', 'admin')),
  created_at timestamptz default now()
);

-- auto‑create profile on signup
create or replace function public.handle_new_user()
returns trigger as $$
begin
  insert into public.profiles (id, role) values (new.id, 'member');
  return new;
end;
$$ language plpgsql security definer;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
