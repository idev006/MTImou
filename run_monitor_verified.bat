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

if "%IMOU_MONITOR_RUNS%"=="" set "IMOU_MONITOR_RUNS=12"
if "%IMOU_MONITOR_INTERVAL_SEC%"=="" set "IMOU_MONITOR_INTERVAL_SEC=8"
if "%IMOU_MONITOR_PER_RUN_TIMEOUT_SEC%"=="" set "IMOU_MONITOR_PER_RUN_TIMEOUT_SEC=150"
if "%IMOU_FFPLAY_VERIFY_SEC%"=="" set "IMOU_FFPLAY_VERIFY_SEC=5"
if "%IMOU_FFPLAY_AUTOEXIT_SEC%"=="" set "IMOU_FFPLAY_AUTOEXIT_SEC=15"
if "%IMOU_SKIP_PROBE_ON_FFPLAY%"=="" set "IMOU_SKIP_PROBE_ON_FFPLAY=1"
if "%IMOU_RTSP_SUBTYPE%"=="" set "IMOU_RTSP_SUBTYPE=0"
if "%IMOU_MONITOR_LOGS_DIR%"=="" set "IMOU_MONITOR_LOGS_DIR=%~dp0logs"

echo [INFO] Running verified viewer monitor...
echo [INFO] IMOU_MONITOR_RUNS=%IMOU_MONITOR_RUNS%
echo [INFO] IMOU_MONITOR_INTERVAL_SEC=%IMOU_MONITOR_INTERVAL_SEC%
echo [INFO] IMOU_MONITOR_PER_RUN_TIMEOUT_SEC=%IMOU_MONITOR_PER_RUN_TIMEOUT_SEC%
echo [INFO] IMOU_FFPLAY_VERIFY_SEC=%IMOU_FFPLAY_VERIFY_SEC%
echo [INFO] IMOU_FFPLAY_AUTOEXIT_SEC=%IMOU_FFPLAY_AUTOEXIT_SEC%

"%PYTHON_EXE%" -u src\monitor_verified_viewer.py
set "RC=%ERRORLEVEL%"
echo [INFO] Exit code: %RC%
exit /b %RC%
