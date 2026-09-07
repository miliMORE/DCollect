DCollect
========

County Public Service salary and remuneration survey.

Python 3.11 or later is required.

Start
-----
Windows:  double-click run.bat
          or:  run.bat local
          or:  run.bat production

Linux/macOS:
          chmod +x run.sh
          ./run.sh
          ./run.sh local
          ./run.sh production

Fresh machine or fresh server
-----------------------------
This is a first-time install: empty folder, no database yet.

Windows (this computer or a Windows server):
  Unzip, then double-click run.bat and choose 1 (local test) or 2
  (production). Or:  run.bat local   /   run.bat production

Linux / macOS server (including Ubuntu VPS):
  Unzip, then:
    chmod +x run.sh
    ./run.sh
  Choose 2 for production (gunicorn on port 8000).
  Or:  ./run.sh production

First run creates .venv, .env, applies migrations, loads catalogues and
starter accounts, and (in production) collects static files. No county
files or survey answers are created.

After the first production start, edit .env:
  DEBUG=false
  ALLOWED_HOSTS=your.hostname.or.ip
  CSRF_TRUSTED_ORIGINS=https://your.hostname
Then restart. Change every starter password at first sign-in.

Keep the process running (systemd, tmux or similar). Default listen
address is 0.0.0.0:8000. Set PORT to use another port.

Existing live site
------------------
Copy these files over the current project. Do not replace db.sqlite3,
.env, .venv or media. Then:

  .venv/bin/python manage.py migrate
  .venv/bin/python manage.py collectstatic --noinput

(On Windows use .venv\Scripts\python.exe.) Restart the app.

Starter accounts (change after first sign-in)
---------------------------------------------
Password: ChangeMe!2026  (or BOOTSTRAP_PASSWORD in .env)

  admin        Platform administrator
  admin2       Collection administrator
  consultant   Field consultant
  analyst      Analyst

Create county respondent accounts under Users after you sign in as admin.
Open county files from Variables & settings when you are ready to collect.

Local test:  http://127.0.0.1:8000/
Production on this machine: port 8000, DEBUG off.

Hosted production (Render or similar): set SECRET_KEY, DEBUG=false,
ALLOWED_HOSTS and CSRF_TRUSTED_ORIGINS (include https://collect.internetcongress.org
if that is the public URL), then use the start command in Procfile / render.yaml.

The full user manual is docs/DCollect-User-Manual.pdf (also on the Desktop
as DCollect User Manual.pdf). Platform administrators download it from the
left menu: User manual (PDF).

Do not copy .env or db.sqlite3 into the zip or into git.
