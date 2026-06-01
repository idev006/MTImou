@echo off
setlocal

cd /d "%~dp0"

if exist "camera.env.bat" (
  call "camera.env.bat"
)

set "IMOU_FORCE_RELAY=1"
set "IMOU_RTSP_INCLUDE_AUTH=1"
set "IMOU_RTSP_TRY_ANON=0"
set "IMOU_USE_FFPROBE=0"
set "IMOU_ONE_URL_PER_TUNNEL=1"
if "%IMOU_RELAY_ATTEMPTS%"=="" set "IMOU_RELAY_ATTEMPTS=5"
if "%IMOU_FRAME_WAIT_SEC%"=="" set "IMOU_FRAME_WAIT_SEC=18"

echo [INFO] Starting remote stream test (free dh-p2p relay mode)...
call "%~dp0run_relay_test.bat"
set "RC=%ERRORLEVEL%"
echo [INFO] Finished with exit code: %RC%
exit /b %RC%
