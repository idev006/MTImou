@echo off
setlocal
cd /d "%~dp0"
call "%~dp0set_python_utf8_env.bat"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Missing venv python: %PY%
  echo [INFO] Run setup_windows.bat first.
  exit /b 101
)

"%PY%" "%~dp0src\control_panel_smoke_audit.py"
exit /b %ERRORLEVEL%
