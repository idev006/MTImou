@echo off
setlocal

cd /d "%~dp0"

set "IMOU_VERIFIED_VIEWER=opencv"
set "IMOU_FORCE_RELAY=1"
set "IMOU_RTSP_SUBTYPE=1"
set "IMOU_NO_FRAME_RESTART_SEC=20"
set "IMOU_BOOTSTRAP_ATTEMPTS=4"
set "IMOU_FIRST_FRAME_TIMEOUT_SEC=12"

call "%~dp0run_stop_all.bat"
call "%~dp0run_viewer_opencv.bat" 0
