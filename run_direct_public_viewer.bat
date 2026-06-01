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

if "%IMOU_PUBLIC_RTSP_HOST%"=="" set "IMOU_PUBLIC_RTSP_HOST=125.27.213.148"
if "%IMOU_PUBLIC_RTSP_PORT%"=="" set "IMOU_PUBLIC_RTSP_PORT=45554"
if "%IMOU_PUBLIC_RTSP_CHANNEL%"=="" set "IMOU_PUBLIC_RTSP_CHANNEL=1"
if "%IMOU_PUBLIC_RTSP_SUBTYPE%"=="" set "IMOU_PUBLIC_RTSP_SUBTYPE=0"
if "%IMOU_CAMERA_USERNAME%"=="" set "IMOU_CAMERA_USERNAME=admin"

"%PY%" "%~dp0src\direct_rtsp_ffplay.py"
exit /b %ERRORLEVEL%
