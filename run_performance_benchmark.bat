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

if "%IMOU_PERF_MODE%"=="" set "IMOU_PERF_MODE=public"
if "%IMOU_PERF_DURATION_SEC%"=="" set "IMOU_PERF_DURATION_SEC=10"
if "%IMOU_PERF_WARMUP_SEC%"=="" set "IMOU_PERF_WARMUP_SEC=2"
if "%IMOU_PERF_MIN_FPS%"=="" set "IMOU_PERF_MIN_FPS=16"
if "%IMOU_REMOTE_MULTI_SUBTYPE%"=="" set "IMOU_REMOTE_MULTI_SUBTYPE=1"
if "%IMOU_PERF_LOG_PATH%"=="" set "IMOU_PERF_LOG_PATH=%~dp0logs\performance_benchmark_latest.log"

"%PY%" "%~dp0src\performance_benchmark.py" %*
exit /b %ERRORLEVEL%
