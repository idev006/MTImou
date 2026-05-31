@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Missing venv activate script: .venv\Scripts\activate.bat
  exit /b 1
)

call ".venv\Scripts\activate.bat"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  echo [ERROR] Missing python exe: %PYTHON_EXE%
  exit /b 1
)

echo [INFO] Scanning LAN for RTSP port 554...
"%PYTHON_EXE%" src\find_camera_ip.py
set "RC=%ERRORLEVEL%"
echo [INFO] Exit code: %RC%
exit /b %RC%
