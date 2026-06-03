@echo off
setlocal
cd /d "%~dp0"
call "%~dp0set_python_utf8_env.bat"

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Missing venv python: %PY%
  exit /b 101
)

if exist "camera.env.bat" (
  call "camera.env.bat"
)

if "%IMOU_SOURCE_CAPABILITY_MODE%"=="" set "IMOU_SOURCE_CAPABILITY_MODE=public"
if "%IMOU_SOURCE_CAPABILITY_DURATION_SEC%"=="" set "IMOU_SOURCE_CAPABILITY_DURATION_SEC=10"
if "%IMOU_SOURCE_CAPABILITY_LOG_PATH%"=="" set "IMOU_SOURCE_CAPABILITY_LOG_PATH=%~dp0logs\source_capability_latest.log"

"%PY%" "%~dp0src\source_capability_check.py" %*
exit /b %ERRORLEVEL%
