@echo off
setlocal
cd /d "%~dp0"
call "%~dp0set_python_utf8_env.bat"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Missing venv python: %PY%
  exit /b 101
)

if exist "camera.env.bat" (
  call "camera.env.bat"
)

if "%IMOU_RESILIENCE_DURATION_SEC%"=="" set "IMOU_RESILIENCE_DURATION_SEC=8"
if "%IMOU_RESILIENCE_MIN_FRAMES%"=="" set "IMOU_RESILIENCE_MIN_FRAMES=10"
if "%IMOU_RESILIENCE_MODES%"=="" set "IMOU_RESILIENCE_MODES=auto,lan,ddns,public"
if "%IMOU_DIRECT_RTSP_TRANSPORT%"=="" set "IMOU_DIRECT_RTSP_TRANSPORT=tcp"
if "%IMOU_DIRECT_NO_FRAME_RESTART_SEC%"=="" set "IMOU_DIRECT_NO_FRAME_RESTART_SEC=8"
if "%IMOU_DIRECT_RECONNECT_SLEEP_SEC%"=="" set "IMOU_DIRECT_RECONNECT_SLEEP_SEC=1.5"
if "%IMOU_DIRECT_FIRST_FRAME_TIMEOUT_SEC%"=="" set "IMOU_DIRECT_FIRST_FRAME_TIMEOUT_SEC=6"
if "%IMOU_TARGET_PROBE_TIMEOUT_SEC%"=="" set "IMOU_TARGET_PROBE_TIMEOUT_SEC=1.2"

"%PY%" "%~dp0src\resilience_smoke.py" %*
exit /b %ERRORLEVEL%
