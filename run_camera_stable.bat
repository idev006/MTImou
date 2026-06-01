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

if "%~1"=="" (
  echo Usage: run_camera_stable.bat ^<camera-id^>
  echo Example: run_camera_stable.bat cam1
  exit /b 2
)

set "IMOU_DIRECT_RTSP_TRANSPORT=tcp"
set "IMOU_DIRECT_NO_FRAME_RESTART_SEC=8"
set "IMOU_DIRECT_RECONNECT_SLEEP_SEC=1.5"
set "IMOU_DIRECT_FIRST_FRAME_TIMEOUT_SEC=6"

"%PY%" "%~dp0src\run_camera_stable.py" %*
exit /b %ERRORLEVEL%
