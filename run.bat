@echo off
setlocal EnableExtensions
cd /d "%~dp0"

set "MODE=%~1"
if /I "%MODE%"=="local" goto START_LOCAL
if /I "%MODE%"=="test" goto START_LOCAL
if /I "%MODE%"=="production" goto START_PROD
if /I "%MODE%"=="prod" goto START_PROD

echo.
echo  DCollect
echo  --------------------------------
echo   1  Local test     http://127.0.0.1:8000/
echo   2  Production     http://0.0.0.0:8000/
echo   3  Exit
echo.
choice /C 123 /N /M "Choose 1, 2 or 3: "
if errorlevel 3 goto END
if errorlevel 2 goto START_PROD
if errorlevel 1 goto START_LOCAL
goto END

:PREP
echo.
echo  Setting up...
call :FIND_PYTHON
if not defined PYLAUNCHER (
  echo  Python 3.11+ was not found. Install it and tick "Add python.exe to PATH".
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo  Creating virtual environment...
  %PYLAUNCHER% -m venv .venv
  if errorlevel 1 exit /b 1
)
set "PY=.venv\Scripts\python.exe"
"%PY%" -m pip install -q --upgrade pip
"%PY%" -m pip install -q -r requirements.txt
if errorlevel 1 exit /b 1
if not exist ".env" (
  if exist ".env.example" (
    "%PY%" -c "from pathlib import Path; import secrets; t=Path('.env.example').read_text(encoding='utf-8'); t=t.replace('change-this-to-a-long-random-string', secrets.token_urlsafe(48)); Path('.env').write_text(t, encoding='utf-8')"
    echo  Created .env
  )
)
if not exist "media" mkdir media
"%PY%" manage.py migrate --noinput
if errorlevel 1 exit /b 1
"%PY%" manage.py bootstrap
if errorlevel 1 exit /b 1
exit /b 0

:FIND_PYTHON
set "PYLAUNCHER="
where py >nul 2>&1 && set "PYLAUNCHER=py -3"
if not defined PYLAUNCHER where python >nul 2>&1 && set "PYLAUNCHER=python"
exit /b 0

:START_LOCAL
call :PREP
if errorlevel 1 goto FAIL
echo.
echo  Local test. Open http://127.0.0.1:8000/
echo  Stop with Ctrl+C
echo.
set DEBUG=true
"%PY%" manage.py runserver 127.0.0.1:8000
goto END

:START_PROD
call :PREP
if errorlevel 1 goto FAIL
echo.
echo  Production. Open http://127.0.0.1:8000/  (or this machine's IP on port 8000)
echo  Stop with Ctrl+C
echo.
"%PY%" manage.py collectstatic --noinput
set DEBUG=false
set ALLOW_ALL_HOSTS=true
set SECURE_COOKIES=false
"%PY%" -m waitress --listen=0.0.0.0:8000 config.wsgi:application
goto END

:FAIL
echo.
echo  Setup failed.
pause
exit /b 1

:END
endlocal
exit /b 0
