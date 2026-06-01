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

set "IMOU_DIRECT_RTSP_TRANSPORT=tcp"
set "IMOU_DIRECT_NO_FRAME_RESTART_SEC=8"
set "IMOU_DIRECT_RECONNECT_SLEEP_SEC=1.5"
set "IMOU_DIRECT_FIRST_FRAME_TIMEOUT_SEC=6"
set "IMOU_TARGET_PROBE_TIMEOUT_SEC=1.2"
set "IMOU_MULTI_LOG_PATH=%~dp0logs\multi_camera_latest.log"

"%PY%" "%~dp0src\multi_camera_view.py" %*
exit /b %ERRORLEVEL%
