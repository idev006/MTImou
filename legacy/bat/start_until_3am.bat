@echo off
setlocal
cd /d "%~dp0"

echo [INFO] Starting overnight runner (hidden)...
start "" powershell -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0run_until_3am.ps1"
echo [INFO] Runner launched.
