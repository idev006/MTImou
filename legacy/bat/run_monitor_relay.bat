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

if "%DH_P2P_REPO_DIR%"=="" set "DH_P2P_REPO_DIR=%~dp0dh-p2p"
if "%IMOU_CAMERA_USERNAME%"=="" set "IMOU_CAMERA_USERNAME=admin"
if "%IMOU_CAMERA_TYPE%"=="" set "IMOU_CAMERA_TYPE=1"
if "%IMOU_FORCE_RELAY%"=="" set "IMOU_FORCE_RELAY=1"
if "%IMOU_RTSP_SUBTYPE%"=="" set "IMOU_RTSP_SUBTYPE=0"
if "%IMOU_RTSP_HOST%"=="" set "IMOU_RTSP_HOST=127.0.0.1"
if "%IMOU_RTSP_PORT%"=="" set "IMOU_RTSP_PORT=554"
if "%IMOU_RTSP_CHANNEL%"=="" set "IMOU_RTSP_CHANNEL=1"
if "%IMOU_MONITOR_RUNS%"=="" set "IMOU_MONITOR_RUNS=6"
if "%IMOU_MONITOR_INTERVAL_SEC%"=="" set "IMOU_MONITOR_INTERVAL_SEC=6"
if "%IMOU_MONITOR_LOGS_DIR%"=="" set "IMOU_MONITOR_LOGS_DIR=%~dp0logs"
set "IMOU_MONITOR_PYTHON_EXE=%PYTHON_EXE%"

echo [INFO] Running relay monitor...
echo [INFO] IMOU_MONITOR_RUNS=%IMOU_MONITOR_RUNS%
echo [INFO] IMOU_MONITOR_INTERVAL_SEC=%IMOU_MONITOR_INTERVAL_SEC%
"%PYTHON_EXE%" -u src\monitor_relay.py
set "RC=%ERRORLEVEL%"
echo [INFO] Exit code: %RC%
exit /b %RC%

