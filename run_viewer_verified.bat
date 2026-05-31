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

set "IMOU_REQUIRED_PYTHON=%PYTHON_EXE%"
set "IMOU_TUNNEL_PYTHON_EXE=%PYTHON_EXE%"

if exist "camera.env.bat" (
  call "camera.env.bat"
)

if "%DH_P2P_REPO_DIR%"=="" set "DH_P2P_REPO_DIR=%~dp0dh-p2p"
if "%IMOU_CAMERA_USERNAME%"=="" set "IMOU_CAMERA_USERNAME=admin"
if "%IMOU_CAMERA_TYPE%"=="" set "IMOU_CAMERA_TYPE=1"
if "%IMOU_FORCE_RELAY%"=="" set "IMOU_FORCE_RELAY=1"
if "%IMOU_RTSP_HOST%"=="" set "IMOU_RTSP_HOST=127.0.0.1"
if "%IMOU_RTSP_PORT%"=="" set "IMOU_RTSP_PORT=554"
if "%IMOU_RTSP_CHANNEL%"=="" set "IMOU_RTSP_CHANNEL=1"
if "%IMOU_RTSP_SUBTYPE%"=="" set "IMOU_RTSP_SUBTYPE=0"
if "%IMOU_RELAY_ATTEMPTS%"=="" set "IMOU_RELAY_ATTEMPTS=4"
if "%IMOU_FRAME_WAIT_SEC%"=="" set "IMOU_FRAME_WAIT_SEC=8"
if "%FFMPEG_BIN_DIR%"=="" set "FFMPEG_BIN_DIR=F:\ffmpeg\bin"

if not "%~1"=="" set "IMOU_RTSP_SUBTYPE=%~1"

echo [INFO] Running verified viewer (probe first, then play)...
call "%~dp0run_stop_all.bat" >nul 2>&1
"%PYTHON_EXE%" -u src\relay_verified_viewer.py
set "RC=%ERRORLEVEL%"
echo [INFO] Exit code: %RC%
exit /b %RC%
