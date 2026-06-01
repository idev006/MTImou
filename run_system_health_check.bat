@echo off
setlocal
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Missing venv python: %PY%
  exit /b 101
)

if exist "camera.env.bat" (
  call "camera.env.bat"
)

set "IMOU_HEALTH_TCP_TIMEOUT_SEC=2.0"
set "IMOU_HEALTH_FRAME_TIMEOUT_SEC=5.0"
set "IMOU_HEALTH_LOG_PATH=%~dp0logs\system_health_check_latest.log"

"%PY%" "%~dp0src\system_health_check.py" %*
exit /b %ERRORLEVEL%
