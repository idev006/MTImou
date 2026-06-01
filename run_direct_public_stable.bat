@echo off
setlocal
cd /d "%~dp0"

if exist "camera.env.bat" (
  call "camera.env.bat"
)

set "IMOU_PUBLIC_RTSP_HOST=125.27.213.148"
set "IMOU_PUBLIC_RTSP_PORT=45554"
set "IMOU_PUBLIC_RTSP_CHANNEL=1"
set "IMOU_PUBLIC_RTSP_SUBTYPE=0"
set "IMOU_DIRECT_RTSP_TRANSPORT=tcp"
set "IMOU_DIRECT_NO_FRAME_RESTART_SEC=8"
set "IMOU_DIRECT_RECONNECT_SLEEP_SEC=1.5"
set "IMOU_DIRECT_FIRST_FRAME_TIMEOUT_SEC=6"

call "%~dp0run_direct_public_opencv.bat"
exit /b %ERRORLEVEL%
