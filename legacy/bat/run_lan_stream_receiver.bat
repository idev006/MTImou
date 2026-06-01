@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
  echo [ERROR] Missing venv activate script: .venv\Scripts\activate.bat
  exit /b 1
)
call ".venv\Scripts\activate.bat"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
  echo [ERROR] Missing python exe: %PYTHON_EXE%
  exit /b 1
)

if exist "camera.env.bat" (
  call "camera.env.bat"
)

if "%IMOU_CAMERA_IP%"=="" set "IMOU_CAMERA_IP=192.168.1.2"
if "%IMOU_CAMERA_USERNAME%"=="" set "IMOU_CAMERA_USERNAME=admin"
if "%IMOU_CAMERA_RTSP_PORT%"=="" set "IMOU_CAMERA_RTSP_PORT=554"
if "%IMOU_RTSP_CHANNEL%"=="" set "IMOU_RTSP_CHANNEL=1"
if "%IMOU_RTSP_SUBTYPE%"=="" set "IMOU_RTSP_SUBTYPE=0"
if "%IMOU_RECEIVER_TARGET_FRAMES%"=="" set "IMOU_RECEIVER_TARGET_FRAMES=60"

if "%IMOU_CAMERA_PASSWORD%"=="" (
  set /p IMOU_CAMERA_PASSWORD=Enter IMOU_CAMERA_PASSWORD: 
)

echo [INFO] Running LAN stream receiver...
"%PYTHON_EXE%" -u src\lan_stream_receiver.py
set "RC=%ERRORLEVEL%"
echo [INFO] Exit code: %RC%
exit /b %RC%
