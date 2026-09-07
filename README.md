# DCollect

County Public Service **salary and remuneration survey** platform. Built with Django for collection, catalogue management, reporting, and admin workflows.

Live (example host): `https://collect.internetcongress.org/`

## Stack

- Python 3.11+
- Django 5.1+
- SQLite (local / default)
- Gunicorn or Waitress for production
- openpyxl for workbook exports
- Render-friendly (`render.yaml`, `Procfile`)

## Features

- Role-based starter accounts (platform admin, collection admin, consultant, analyst)
- County respondent accounts managed by admins
- Catalogues, variables & settings, and county file workflows
- Document attachments (multiple files per heading; zip downloads)
- Benefits matrix and related survey sections
- Workbook + attachments “download complete file”
- Idle sign-out after inactivity
- Audit trail for administrators
- User manual PDF (`docs/DCollect-User-Manual.pdf`) for platform admins

## Quick start (fresh machine)

```bash
# Linux / macOS
chmod +x run.sh
./run.sh            # or: ./run.sh local | ./run.sh production

# Windows
run.bat             # or: run.bat local | run.bat production
```

First run creates `.venv`, `.env`, applies migrations, loads catalogues and starter accounts, and (in production) collects static files.

Then edit `.env` for production:

```
DEBUG=false
ALLOWED_HOSTS=your.hostname.or.ip
CSRF_TRUSTED_ORIGINS=https://your.hostname
```

Change every starter password at first sign-in. Default bootstrap password is `ChangeMe!2026` (or `BOOTSTRAP_PASSWORD` in `.env`).

Local: http://127.0.0.1:8000/  
Production default listen: `0.0.0.0:8000` (override with `PORT`).

## Updating an existing live site

Copy application files over the current project. **Do not replace** `db.sqlite3`, `.env`, `.venv`, or `media/`. Then:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py collectstatic --noinput
```

Restart the app process. Do **not** re-run bootstrap/`run.sh` on a live server.

## Hosted production

Set `SECRET_KEY`, `DEBUG=false`, `ALLOWED_HOSTS`, and `CSRF_TRUSTED_ORIGINS`. Use the start command in `Procfile` / `render.yaml`.

## Security notes

Do not commit or ship `.env` or `db.sqlite3`. See `.env.example` and `.gitignore`.
