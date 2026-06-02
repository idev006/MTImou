@echo off
setlocal
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Missing venv python: %PY%
  echo [INFO] Run setup_windows.bat first.
  exit /b 101
)

if exist "camera.env.bat" (
  call "camera.env.bat"
)

if not exist "camera.env.bat" if exist "camera.env.bat.example" (
  copy /y "camera.env.bat.example" "camera.env.bat" >nul
  echo [INFO] Created camera.env.bat from camera.env.bat.example
)

"%PY%" "%~dp0src\control_panel.py"
exit /b %ERRORLEVEL%
