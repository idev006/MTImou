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

if "%IMOU_TARGET_MODE%"=="" set "IMOU_TARGET_MODE=public"
if "%IMOU_REMOTE_SINGLE_SUBTYPE%"=="" set "IMOU_REMOTE_SINGLE_SUBTYPE=0"

"%PY%" "%~dp0src\launch_split_viewers.py" %*
exit /b %ERRORLEVEL%
