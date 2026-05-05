# Mission Tracker — ARCHITECTURE_2.md
> Version 2 design document. Supersedes ARCHITECTURE.md.

---

## 1. What Changes and Why

Version 1 is functional but has several structural problems that compound as the club grows: raw HTML templates with no design system, no mobile layout, N+1 database queries, an XSS hole in comments, a broken admin user-creation flow, and missing features that leads and members would actually want (due dates, priorities, file evidence, a Kanban view, personal task inbox). Version 2 addresses all of these in a single coherent redesign while keeping the same Python-only, single-codebase philosophy.

---

## 2. Tech Stack (changes from v1 highlighted)

| Layer | v1 | v2 |
|---|---|---|
| Web framework | FastAPI | FastAPI (unchanged) |
| Templates | Jinja2 (no CSS framework) | Jinja2 + **TailwindCSS CDN** + **Alpine.js** |
| Interactivity | HTMX (partial) | HTMX (expanded) + **Alpine.js** |
| Database | Supabase PostgreSQL | Supabase PostgreSQL (schema additions) |
| Auth | Supabase email/password + cookies | Same + **admin uses `auth.admin.create_user`** |
| File storage | — | **Supabase Storage** (task attachments) |
| Deployment | Vercel | Vercel (unchanged) |

**Why TailwindCSS CDN?**
No build step. Drop one `<script>` tag in the base template. Gives full utility-class coverage for responsive layouts, dark mode, and consistent spacing/typography without writing any custom CSS.

**Why Alpine.js?**
Fills the gap between Jinja2 and full React. Handles dropdowns, modals, tab switches, and toggle states with `x-data`/`x-show`/`x-on` attributes directly in HTML. Zero-config, 15kb. Pairs perfectly with HTMX.

**Why not switch to Next.js / React?**
The existing Python codebase, Supabase integration, and Vercel deployment are all working. Rewriting the frontend in React would double the codebase with no functional gain at club scale. The Tailwind+Alpine+HTMX stack ("TAAH") achieves 95% of the interactivity React would offer from pure HTML templates.

---

## 3. Roles & Permissions (unchanged from v1)

| Role | View | Create/Edit Missions/Projects | Add Task | Assign Task | Update Task Status | Comment | Manage Users | Audit Log |
|---|---|---|---|---|---|---|---|---|
| member | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| lead | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 4. Database Schema Changes

### 4.1 Profiles (addition: `display_name` and `username` already in v1 code but not in ARCHITECTURE.md)

```sql
create table public.profiles (
  id            uuid references auth.users primary key,
  role          text not null default 'member' check (role in ('member', 'lead', 'admin')),
  username      text unique,
  display_name  text,
  avatar_url    text,           -- NEW: Supabase Storage URL for profile picture
  created_at    timestamptz default now()
);
```

### 4.2 Missions (unchanged)

```sql
create table public.missions (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  description text,
  created_at  timestamptz default now()
);
```

### 4.3 Projects (unchanged)

```sql
create table public.projects (
  id          uuid primary key default gen_random_uuid(),
  mission_id  uuid references missions(id) on delete cascade,
  name        text not null,
  description text,
  lead_id     uuid references profiles(id) on delete set null,
  created_at  timestamptz default now()
);
```

### 4.4 Tasks (additions: `due_date`, `priority`)

```sql
create table public.tasks (
  id          uuid primary key default gen_random_uuid(),
  project_id  uuid references projects(id) on delete cascade,
  title       text not null,
  description text,
  status      text not null default 'todo' check (status in ('todo', 'in_progress', 'done')),
  priority    text not null default 'medium' check (priority in ('low', 'medium', 'high')), -- NEW
  due_date    date,                                                                          -- NEW
  created_at  timestamptz default now(),
  updated_at  timestamptz default now()
);
```

### 4.5 Task Assignees (unchanged)

```sql
create table public.task_assignees (
  task_id   uuid references tasks(id) on delete cascade,
  user_id   uuid references profiles(id) on delete cascade,
  primary key (task_id, user_id)
);
```

### 4.6 Task Attachments (NEW)

Stores evidence files for tasks. Actual files live in Supabase Storage bucket `task-attachments`.

```sql
create table public.task_attachments (
  id           uuid primary key default gen_random_uuid(),
  task_id      uuid references tasks(id) on delete cascade,
  uploader_id  uuid references profiles(id) on delete set null,
  file_name    text not null,
  storage_path text not null,   -- path in Supabase Storage bucket
  mime_type    text,
  file_size    int,             -- bytes
  created_at   timestamptz default now()
);
```

**Supabase Storage bucket:** `task-attachments`, private. Access via signed URLs generated per request. Allowed types: images (jpg/png/webp), PDF, common document formats. 20MB per file limit enforced at upload.

### 4.7 Comments (addition: `updated_at`, soft XSS fix via server-side escaping)

```sql
create table public.comments (
  id         uuid primary key default gen_random_uuid(),
  task_id    uuid references tasks(id) on delete cascade,
  user_id    uuid references profiles(id) on delete set null,
  content    text not null,
  created_at timestamptz default now(),
  updated_at timestamptz default now()  -- NEW (for future edit support)
);
```

### 4.8 Audit Logs (unchanged)

```sql
create table public.audit_logs (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid references profiles(id) on delete set null,
  action      text not null,
  entity_type text not null,
  entity_id   text not null,
  old_values  jsonb,
  new_values  jsonb,
  created_at  timestamptz default now()
);
```

---

## 5. Bug Fixes Elevated to Architectural Changes

### 5.1 XSS in comment rendering (SECURITY)

**v1 problem:** `add_comment` in `main.py` builds HTML with a raw f-string: `f"<p>{content}</p>"`. If a user submits `<script>alert(1)</script>`, it executes in the browser.

**v2 fix:** All HTMX partial responses must go through a Jinja2 template fragment, never an f-string. The `autoescape=True` on the Jinja2 `Environment` already handles escaping. Remove all inline HTML construction from route handlers.

```python
# v1 (WRONG)
comment_html = f"<p>{content}</p>"
return HTMLResponse(comment_html)

# v2 (CORRECT)
return HTMLResponse(env.get_template("_comment.html").render(
    comment=new_comment, username=username_map.get(user['id'], 'Unknown')
))
```

### 5.2 N+1 in `get_monthly_progress` (PERFORMANCE)

**v1 problem:** For each completed task, a separate `task_assignees` query runs in a Python loop — O(n) Supabase round trips.

**v2 fix:** Fetch all assignee rows for the entire set of completed task IDs in one query, then group in Python.

```python
# v2 approach
task_ids = [c["id"] for c in completed_tasks]
if task_ids:
    all_assignee_rows = supabase.table("task_assignees") \
        .select("task_id, user_id") \
        .in_("task_id", task_ids) \
        .execute().data
    # group by task_id in Python — zero extra round trips
```

### 5.3 `create_user_by_admin` uses `sign_up` (BEHAVIOUR)

**v1 problem:** Admin-created users receive a confirmation email and cannot log in until they confirm. Unusable for adding club members directly.

**v2 fix:** Use the Supabase service-role admin API to create users without email confirmation.

```python
# v2
from supabase import Client
# use admin client (service role key) for this operation only
admin_client.auth.admin.create_user({
    "email": email,
    "password": password,
    "email_confirm": True   # bypass confirmation
})
```

The `database.py` module should expose two clients: `supabase` (anon key, used for all user-facing reads/writes) and `supabase_admin` (service role key, used only for `create_user_by_admin`).

### 5.4 Bulk insert in `assign_users_to_task` (PERFORMANCE)

**v1 problem:** Individual `INSERT` per assignee in a loop.

**v2 fix:** Single bulk insert.

```python
rows = [{"task_id": task_id, "user_id": uid} for uid in user_ids if uid]
if rows:
    supabase.table("task_assignees").insert(rows).execute()
```

### 5.5 `get_username_map()` called per request (PERFORMANCE)

**v1 problem:** Fetches all profiles on every route that needs display names. Cheap now, but wasteful.

**v2 fix:** Cache with a short TTL (60 seconds) using a module-level dict + timestamp. At club scale a simple in-process cache is enough — no Redis needed.

```python
_username_cache: dict = {}
_username_cache_ts: float = 0.0
CACHE_TTL = 60  # seconds

def get_username_map():
    global _username_cache, _username_cache_ts
    if time.time() - _username_cache_ts > CACHE_TTL:
        users = crud.get_all_users_detailed()
        _username_cache = {u["id"]: u["username"] or u["display_name"] or u["id"] for u in users}
        _username_cache_ts = time.time()
    return _username_cache
```

---

## 6. New Features

### 6.1 My Tasks Inbox

A `/my-tasks` route showing all tasks assigned to the logged-in user, grouped by status. Every role can see this — it is the primary landing page for members (who otherwise have view-only access to everything else). Shows due date, priority badge, and parent project name.

### 6.2 Task Priority

Tasks now have a `priority` field (low / medium / high). Rendered as a colour-coded badge: green/yellow/red. Leads and admins can set priority at creation or edit time. The Kanban and task list are sortable by priority.

### 6.3 Due Dates

Tasks have an optional `due_date` (date, not timestamp). The UI shows a countdown pill: "3 days left" in yellow, "Overdue" in red, "Today" in orange. The Kanban and task list can be filtered by overdue/upcoming.

### 6.4 Kanban Board View

Each project page gains a Kanban toggle (list ↔ board). The board shows three columns: To Do / In Progress / Done. Drag-and-drop via **Sortable.js** (CDN) triggers an HTMX POST to update status. On mobile, columns stack vertically with horizontal scroll per column. Only leads and admins can drag cards.

### 6.5 Task Attachments

Leads and admins can upload files (evidence, photos, docs) to any task. Files are stored in Supabase Storage. The task detail page shows a gallery of thumbnails for images and file icons for other types. Each file is served via a short-lived signed URL (1 hour). Upload progress is shown inline via HTMX.

### 6.6 Overdue / Due-Soon Alerts on Dashboard

The dashboard shows a callout section for tasks that are overdue or due within 3 days across all missions the user can see, regardless of assignment. Keeps leads informed about at-risk work.

### 6.7 Progress Dashboard Improvements

The existing `/progress` page is expanded:
- Visual progress bars per project (completed/total)
- Assignee leaderboard sorted by completions
- Month picker with prev/next navigation
- Export to CSV button (generates a Supabase query client-side via HTMX download link)

---

## 7. UI Architecture

### 7.1 Base Template Structure

A single `base.html` Jinja2 template wraps all pages with:
- TailwindCSS CDN in `<head>`
- Alpine.js CDN in `<head>`
- HTMX CDN in `<head>`
- Sortable.js CDN (for Kanban drag-drop) in `<head>`
- Responsive navbar (hamburger on mobile, full links on desktop)
- Toast notification area (Alpine.js driven, appears bottom-right)
- A `{% block content %}` for page body

### 7.2 Responsive Layout

All pages use a mobile-first grid:

```
Mobile  (< 640px):  single column, stacked sections, full-width cards
Tablet  (640–1024px): 2-col where useful (e.g. missions list)
Desktop (> 1024px):   sidebar nav + main content area
```

Desktop gets a persistent left sidebar (collapsible) with navigation links. Mobile gets a top navbar with a hamburger that slides out a drawer — handled entirely with Alpine.js `x-show` + `x-transition`, no JavaScript files to manage.

### 7.3 Component Library (Jinja2 Macros)

All repeated UI patterns are factored into macros in `templates/macros.html`:

| Macro | Usage |
|---|---|
| `badge(text, color)` | Status badge, priority badge, role badge |
| `task_card(task, assignees, user)` | Kanban card + list row |
| `avatar(profile)` | 32px round avatar with initials fallback |
| `due_pill(due_date)` | Countdown pill with colour logic |
| `empty_state(message, icon)` | Consistent empty list placeholder |
| `confirm_modal(id, message, action_url)` | Delete confirmation modal |

### 7.4 HTMX Usage Map

| Action | HTMX trigger | Target | Swap |
|---|---|---|---|
| Add task | `hx-post` on form | `#task-list` | `innerHTML` |
| Update task status | `hx-post` on status button | `#task-card-{id}` | `outerHTML` |
| Add comment | `hx-post` on comment form | `#comment-list` | `beforeend` |
| Upload attachment | `hx-post` on file input | `#attachment-list` | `beforeend` |
| Search filter change | `hx-get` on select/input | `#search-results` | `innerHTML` |
| Kanban drag-drop | Sortable.js callback → fetch POST | `#task-card-{id}` | `outerHTML` |

All HTMX partials are separate `_partial.html` template files — no inline HTML strings in Python.

### 7.5 Colour System & Dark Mode

TailwindCSS dark mode via `class` strategy (toggle with Alpine.js + `localStorage`). A sun/moon button in the navbar toggles `dark` on `<html>`.

Semantic colour tokens used throughout:

| Token | Light | Dark |
|---|---|---|
| Background | `gray-50` | `gray-900` |
| Surface (cards) | `white` | `gray-800` |
| Border | `gray-200` | `gray-700` |
| Primary accent | `sky-600` | `sky-400` |
| Success | `green-600` | `green-400` |
| Warning | `yellow-500` | `yellow-400` |
| Danger | `red-600` | `red-400` |

### 7.6 Page-by-Page UI Spec

**`/dashboard`**
- Top row: stat cards (total missions, total tasks, overdue tasks, tasks done this month)
- Overdue/due-soon alert strip (if any)
- Mission cards grid (2-col tablet, 3-col desktop, 1-col mobile) with project count, task count, completion ring
- Floating `+` button (admin only) for quick mission create

**`/missions/{id}`**
- Mission header with description
- Project cards in a 2-3 col responsive grid
- Each card: name, lead avatar, task completion bar, status breakdown pills
- Admin: Edit / Delete buttons in card corner menu (Alpine.js dropdown)

**`/projects/{id}`**
- Project header + lead info
- View toggle: List | Kanban (persisted to `localStorage`)
- **Kanban view**: 3 columns (`todo` / `in_progress` / `done`), drag-and-drop cards, task count badge per column
- **List view**: table with title, priority badge, assignee avatars, due pill, status
- Lead/admin: inline Add Task form below column header (Kanban) or at list bottom
- Sticky column headers on desktop Kanban

**`/tasks/{id}`**
- Full-width card: title, description, priority badge, due date, status
- Assignee section with avatars and names
- Attachments gallery (thumbnails + upload zone for lead/admin)
- Comments thread (chronological, avatar + timestamp per comment)
- Status action button (single large button showing next valid state)
- Sidebar (desktop) / collapsible section (mobile): metadata, audit trail for this task

**`/my-tasks`**
- Personal inbox grouped into: Overdue / Due Today / Due This Week / Upcoming / No Due Date
- Each group is a collapsible section (Alpine.js)
- Task rows show project name, priority badge, due pill

**`/progress`**
- Month navigator (prev/next arrow, month display)
- Mission/project completion bars
- Assignee table sorted by completions
- Download CSV button

**`/search`**
- Filter bar: text query, mission select, project select (populated via HTMX on mission change), status radio, date range
- Results as task cards with parent breadcrumb (Mission > Project > Task)

**`/admin/users`**
- Table: avatar, display name, username, role dropdown (inline update via HTMX POST), joined date
- Add User button opens a slide-over panel (Alpine.js) instead of separate page

**`/admin/audit-log`**
- Filterable table: actor, action, entity type, date
- Colour-coded action badges (created=green, updated=yellow, deleted=red)

---

## 8. File Structure

```
mission-tracker/
├── main.py              # All route handlers
├── crud.py              # All DB operations
├── auth.py              # Auth helpers, dependencies
├── database.py          # supabase (anon) + supabase_admin (service role) clients
├── utils.py             # NEW: get_username_map with cache, due_date helpers
├── requirements.txt
├── vercel.json
├── .env                 # SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY
└── templates/
    ├── base.html        # Tailwind + Alpine + HTMX CDN, navbar, toast zone
    ├── macros.html      # Jinja2 macros: badge, avatar, task_card, due_pill, etc.
    ├── dashboard.html
    ├── mission_detail.html
    ├── project_detail.html
    ├── task_detail.html
    ├── my_tasks.html    # NEW
    ├── progress.html
    ├── search.html
    ├── login.html
    ├── signup.html
    ├── admin_users.html
    ├── admin_add_user.html
    ├── audit_log.html
    ├── mission_form.html
    ├── project_form.html
    ├── _task_list.html  # HTMX partial
    ├── _task_card.html  # HTMX partial
    ├── _comment.html    # HTMX partial (replaces f-string in v1)
    ├── _attachment.html # NEW HTMX partial
    └── _search_results.html  # HTMX partial
```

---

## 9. New Routes Summary

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/my-tasks` | Any | Personal task inbox |
| POST | `/tasks/{id}/attachments` | lead/admin | Upload file to task |
| GET | `/tasks/{id}/attachments/{att_id}` | Any | Signed URL redirect for file |
| DELETE | `/tasks/{id}/attachments/{att_id}` | lead/admin | Delete attachment |
| GET | `/projects/{id}?view=kanban` | Any | Kanban view (query param, persisted in localStorage) |
| POST | `/admin/users/{id}/avatar` | admin | Upload admin-set avatar |

---

## 10. What Is NOT Changing

- The FastAPI + Jinja2 + Supabase + Vercel core remains identical
- The Mission → Project → Task three-level hierarchy
- The three-role permission model (member / lead / admin)
- The task state machine (todo → in_progress → done, done is terminal)
- Cookie-based session auth
- Audit logging on all mutations
- Python-only single codebase, no separate frontend repo
