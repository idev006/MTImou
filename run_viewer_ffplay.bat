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

echo [INFO] Cleaning stale viewer/tunnel processes...
for /f "skip=1 tokens=2 delims==" %%P in ('wmic process where "name='python.exe' and (CommandLine like '%%imou_ffplay_viewer.py%%' or CommandLine like '%%dh-p2p\\main.py%%')" get ProcessId /value 2^>nul') do (
  if not "%%P"=="" (
    taskkill /PID %%P /T /F >nul 2>&1
  )
)
taskkill /IM ffplay.exe /T /F >nul 2>&1

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":554 .*LISTENING"') do (
  echo [INFO] Port 554 in use by PID %%P, terminating...
  taskkill /PID %%P /T /F >nul 2>&1
)

if exist "camera.env.bat" (
  call "camera.env.bat"
)

if "%DH_P2P_REPO_DIR%"=="" set "DH_P2P_REPO_DIR=%~dp0dh-p2p"
set "IMOU_TUNNEL_PYTHON_EXE=%PYTHON_EXE%"
if "%IMOU_CAMERA_USERNAME%"=="" set "IMOU_CAMERA_USERNAME=admin"
if "%IMOU_CAMERA_TYPE%"=="" set "IMOU_CAMERA_TYPE=1"
if "%IMOU_FORCE_RELAY%"=="" set "IMOU_FORCE_RELAY=1"
if "%IMOU_RTSP_SUBTYPE%"=="" set "IMOU_RTSP_SUBTYPE=1"
if "%IMOU_RTSP_HOST%"=="" set "IMOU_RTSP_HOST=127.0.0.1"
if "%IMOU_RTSP_PORT%"=="" set "IMOU_RTSP_PORT=554"
if "%IMOU_RTSP_CHANNEL%"=="" set "IMOU_RTSP_CHANNEL=1"
if "%IMOU_STARTUP_WAIT_SEC%"=="" set "IMOU_STARTUP_WAIT_SEC=90"
if "%FFMPEG_BIN_DIR%"=="" set "FFMPEG_BIN_DIR=F:\ffmpeg\bin"
if "%IMOU_FFPLAY_ANALYZEDURATION%"=="" set "IMOU_FFPLAY_ANALYZEDURATION=2000000"
if "%IMOU_FFPLAY_PROBESIZE%"=="" set "IMOU_FFPLAY_PROBESIZE=1000000"
if "%IMOU_STRICT_SUBTYPE%"=="" set "IMOU_STRICT_SUBTYPE=1"
if "%IMOU_FORCE_SUBTYPE1%"=="" set "IMOU_FORCE_SUBTYPE1=1"
if "%IMOU_TRY_CHANNEL0%"=="" set "IMOU_TRY_CHANNEL0=1"
if "%IMOU_FFPLAY_LOW_LATENCY%"=="" set "IMOU_FFPLAY_LOW_LATENCY=0"
if "%IMOU_USE_FFPROBE_PRECHECK%"=="" set "IMOU_USE_FFPROBE_PRECHECK=0"
if "%IMOU_TUNNEL_WARMUP_SEC%"=="" set "IMOU_TUNNEL_WARMUP_SEC=1.2"
if "%IMOU_FFPLAY_TIMEOUT_US%"=="" set "IMOU_FFPLAY_TIMEOUT_US="
if "%IMOU_RTSP_TRANSPORTS%"=="" set "IMOU_RTSP_TRANSPORTS=tcp,udp"
if "%IMOU_FFPLAY_TEST_SECONDS%"=="" set "IMOU_FFPLAY_TEST_SECONDS="
if "%IMOU_KILL_PORT_554%"=="" set "IMOU_KILL_PORT_554=1"
if "%IMOU_FORCE_SUBTYPE1%"=="1" set "IMOU_RTSP_SUBTYPE=1"

if "%IMOU_CAMERA_SN%"=="" (
  set /p IMOU_CAMERA_SN=Enter IMOU_CAMERA_SN: 
)
if "%IMOU_CAMERA_PASSWORD%"=="" (
  set /p IMOU_CAMERA_PASSWORD=Enter IMOU_CAMERA_PASSWORD: 
)

echo [INFO] Starting ffplay viewer...
echo [INFO] IMOU_RTSP_SUBTYPE=%IMOU_RTSP_SUBTYPE% (IMOU_FORCE_SUBTYPE1=%IMOU_FORCE_SUBTYPE1%)
echo [INFO] IMOU_RTSP_CHANNEL=%IMOU_RTSP_CHANNEL% (IMOU_TRY_CHANNEL0=%IMOU_TRY_CHANNEL0%)
echo [INFO] IMOU_FFPLAY_LOW_LATENCY=%IMOU_FFPLAY_LOW_LATENCY%
echo [INFO] IMOU_USE_FFPROBE_PRECHECK=%IMOU_USE_FFPROBE_PRECHECK%
echo [INFO] IMOU_FFPLAY_TIMEOUT_US=%IMOU_FFPLAY_TIMEOUT_US%
echo [INFO] IMOU_RTSP_TRANSPORTS=%IMOU_RTSP_TRANSPORTS%
echo [INFO] IMOU_FFPLAY_TEST_SECONDS=%IMOU_FFPLAY_TEST_SECONDS%
echo [INFO] IMOU_KILL_PORT_554=%IMOU_KILL_PORT_554%
echo [INFO] IMOU_TUNNEL_PYTHON_EXE=%IMOU_TUNNEL_PYTHON_EXE%
"%PYTHON_EXE%" src\imou_ffplay_viewer.py
set "RC=%ERRORLEVEL%"
echo [INFO] Exit code: %RC%
exit /b %RC%
