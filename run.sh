#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-}"

find_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo python3
  elif command -v python >/dev/null 2>&1; then
    echo python
  else
    echo "Python 3.11+ is required." >&2
    exit 1
  fi
}

prep() {
  echo "Setting up..."
  local launcher
  launcher="$(find_python)"
  if [[ ! -x .venv/bin/python ]]; then
    echo "Creating virtual environment..."
    "$launcher" -m venv .venv
  fi
  PY=".venv/bin/python"
  "$PY" -m pip install -q --upgrade pip
  "$PY" -m pip install -q -r requirements.txt
  if [[ ! -f .env && -f .env.example ]]; then
    "$PY" -c "from pathlib import Path; import secrets; t=Path('.env.example').read_text(encoding='utf-8'); t=t.replace('change-this-to-a-long-random-string', secrets.token_urlsafe(48)); Path('.env').write_text(t, encoding='utf-8')"
    echo "Created .env"
  fi
  mkdir -p media staticfiles
  "$PY" manage.py migrate --noinput
  "$PY" manage.py bootstrap
}

if [[ "$MODE" == "" ]]; then
  echo
  echo "DCollect"
  echo "--------------------------------"
  echo "  1  Local test     http://127.0.0.1:8000/"
  echo "  2  Production     gunicorn on PORT (default 8000)"
  echo "  3  Exit"
  echo
  read -r -p "Choose 1, 2 or 3: " CHOICE
  case "$CHOICE" in
    1) MODE=local ;;
    2) MODE=production ;;
    *) exit 0 ;;
  esac
fi

prep
PY=".venv/bin/python"

if [[ "$MODE" == "local" || "$MODE" == "test" ]]; then
  echo
  echo "Local test. Open http://127.0.0.1:8000/"
  echo "Stop with Ctrl+C"
  echo
  export DEBUG=true
  exec "$PY" manage.py runserver 127.0.0.1:8000
fi

if [[ "$MODE" == "production" || "$MODE" == "prod" ]]; then
  echo
  echo "Production. http://127.0.0.1:${PORT:-8000}/"
  echo "Stop with Ctrl+C"
  echo
  "$PY" manage.py collectstatic --noinput
  export DEBUG=false
  export ALLOW_ALL_HOSTS="${ALLOW_ALL_HOSTS:-true}"
  export SECURE_COOKIES="${SECURE_COOKIES:-false}"
  exec "$PY" -m gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --timeout 120 --workers "${WEB_CONCURRENCY:-2}"
fi

echo "Usage: ./run.sh [local|production]"
exit 1
