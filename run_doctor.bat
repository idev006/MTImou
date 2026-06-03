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

if exist "camera.env.bat" (
  call "camera.env.bat"
)

"%PY%" "%~dp0src\doctor.py"
exit /b %ERRORLEVEL%
