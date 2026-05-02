# Development Log

## Chunk 1 – Completed
- GitHub repo created
- Supabase project set up with complete schema (missions, projects, tasks, profiles, audit_logs, comments)
- Profiles auto‑created on signup via trigger
- RLS disabled, email auth enabled
- Local .env, .gitignore, requirements.txt created

Next: Chunk 2 – FastAPI skeleton, virtual env, first route

## Chunk 2 – Completed (final)
- Fixed Jinja2 bug by bypassing Jinja2Templates wrapper
- Home page renders correctly using direct Environment + HTMLResponse
