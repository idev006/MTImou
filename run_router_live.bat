@echo off
setlocal
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Missing venv python: %PY%
  exit /b 101
)

set "ROUTER_USERNAME=admin"
set "ROUTER_PASSWORD=admin"

"%PY%" "%~dp0src\router_live_control.py" --show --keep-open --delay 1.2 %*
exit /b %ERRORLEVEL%
