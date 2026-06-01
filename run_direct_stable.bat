@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

if exist "camera.env.bat" (
  call "camera.env.bat"
)

if "%IMOU_CAMERA_USERNAME%"=="" set "IMOU_CAMERA_USERNAME=admin"
if "%IMOU_CAMERA_PASSWORD%"=="" (
  echo [ERROR] Missing IMOU_CAMERA_PASSWORD
  exit /b 2
)

set "IMOU_PUBLIC_RTSP_SUBTYPE=0"
set "IMOU_DIRECT_RTSP_TRANSPORT=tcp"
set "IMOU_DIRECT_NO_FRAME_RESTART_SEC=8"
set "IMOU_DIRECT_RECONNECT_SLEEP_SEC=1.5"
set "IMOU_DIRECT_FIRST_FRAME_TIMEOUT_SEC=6"

set "LAN_HOST=192.168.1.2"
set "LAN_PORT=554"
set "PUBLIC_HOST=125.27.213.148"
set "PUBLIC_PORT=45554"

set "MODE=public"
powershell -NoProfile -Command "$c = New-Object System.Net.Sockets.TcpClient; try { $iar = $c.BeginConnect('%LAN_HOST%', %LAN_PORT%, $null, $null); if($iar.AsyncWaitHandle.WaitOne(1200) -and $c.Connected){ exit 0 } else { exit 1 } } catch { exit 1 } finally { $c.Close() }"
if "%ERRORLEVEL%"=="0" set "MODE=lan"

if /I "%MODE%"=="lan" (
  echo [INFO] Auto mode selected LAN target %LAN_HOST%:%LAN_PORT%
  set "IMOU_PUBLIC_RTSP_HOST=%LAN_HOST%"
  set "IMOU_PUBLIC_RTSP_PORT=%LAN_PORT%"
  set "IMOU_DIRECT_MODE_LABEL=lan"
  set "IMOU_DIRECT_WINDOW_NAME=IMOU Direct LAN RTSP"
  set "IMOU_DIRECT_LOG_PATH=%~dp0logs\direct_lan_latest.log"
) else (
  echo [INFO] Auto mode selected PUBLIC target %PUBLIC_HOST%:%PUBLIC_PORT%
  set "IMOU_PUBLIC_RTSP_HOST=%PUBLIC_HOST%"
  set "IMOU_PUBLIC_RTSP_PORT=%PUBLIC_PORT%"
  set "IMOU_DIRECT_MODE_LABEL=public"
  set "IMOU_DIRECT_WINDOW_NAME=IMOU Direct Public RTSP"
  set "IMOU_DIRECT_LOG_PATH=%~dp0logs\direct_public_latest.log"
)

call "%~dp0run_direct_public_opencv.bat"
exit /b %ERRORLEVEL%
