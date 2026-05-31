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

REM Free RTSP port 554 if a previous run is still holding it.
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":554 .*LISTENING"') do (
  echo [INFO] Port 554 in use by PID %%P, terminating...
  taskkill /PID %%P /F >nul 2>&1
)

if exist "camera.env.bat" (
  if not "%IMOU_CAMERA_SN%"=="" (
    echo [INFO] Existing IMOU_* env found, skip camera.env.bat
  ) else (
    call "camera.env.bat"
  )
) else (
  echo [INFO] camera.env.bat not found. Using existing environment variables.
)

REM Optional overrides from args:
REM   run_viewer_opencv.bat 1      -> subtype=1
REM   run_viewer_opencv.bat 0 0    -> subtype=0 channel=0
if not "%~1"=="" set "IMOU_RTSP_SUBTYPE=%~1"
if not "%~2"=="" set "IMOU_RTSP_CHANNEL=%~2"

if "%DH_P2P_REPO_DIR%"=="" set "DH_P2P_REPO_DIR=%~dp0dh-p2p"
if "%IMOU_CAMERA_USERNAME%"=="" set "IMOU_CAMERA_USERNAME=admin"
if "%IMOU_CAMERA_TYPE%"=="" set "IMOU_CAMERA_TYPE=1"
if "%IMOU_FORCE_RELAY%"=="" set "IMOU_FORCE_RELAY=1"
if "%IMOU_RTSP_INCLUDE_AUTH%"=="" set "IMOU_RTSP_INCLUDE_AUTH=1"
if "%IMOU_RTSP_SUBTYPE%"=="" set "IMOU_RTSP_SUBTYPE=0"
if "%IMOU_RTSP_HOST%"=="" set "IMOU_RTSP_HOST=127.0.0.1"
if "%IMOU_RTSP_PORT%"=="" set "IMOU_RTSP_PORT=554"
if "%IMOU_RTSP_CHANNEL%"=="" set "IMOU_RTSP_CHANNEL=1"
if "%IMOU_STARTUP_WAIT_SEC%"=="" set "IMOU_STARTUP_WAIT_SEC=90"
if "%IMOU_NO_FRAME_RESTART_SEC%"=="" set "IMOU_NO_FRAME_RESTART_SEC=12"
if "%IMOU_BOOTSTRAP_ATTEMPTS%"=="" set "IMOU_BOOTSTRAP_ATTEMPTS=4"
if "%IMOU_FIRST_FRAME_TIMEOUT_SEC%"=="" set "IMOU_FIRST_FRAME_TIMEOUT_SEC=8"

if "%IMOU_CAMERA_SN%"=="" (
  set /p IMOU_CAMERA_SN=Enter IMOU_CAMERA_SN: 
)
if "%IMOU_CAMERA_PASSWORD%"=="" (
  set /p IMOU_CAMERA_PASSWORD=Enter IMOU_CAMERA_PASSWORD: 
)

echo [INFO] Starting OpenCV viewer...
"%PYTHON_EXE%" src\imou_opencv_spike.py
set "RC=%ERRORLEVEL%"
echo [INFO] Exit code: %RC%
exit /b %RC%
