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

if "%IMOU_OPENAPI_DC%"=="" if "%IMOU_OPENAPI_DOMAIN%"=="" set "IMOU_OPENAPI_DC=sg"
if "%IMOU_OPENAPI_CHANNEL_ID%"=="" set "IMOU_OPENAPI_CHANNEL_ID=0"
if "%IMOU_OPENAPI_STREAM_ID%"=="" set "IMOU_OPENAPI_STREAM_ID=0"

if "%IMOU_APP_ID%"=="" (
  set /p IMOU_APP_ID=Enter IMOU_APP_ID: 
)
if "%IMOU_APP_SECRET%"=="" (
  set /p IMOU_APP_SECRET=Enter IMOU_APP_SECRET: 
)
if "%IMOU_CAMERA_SN%"=="" (
  set /p IMOU_CAMERA_SN=Enter IMOU_CAMERA_SN: 
)

echo [INFO] Running OpenAPI live PoC...
"%PYTHON_EXE%" -u src\imou_openapi_live_poc.py
set "RC=%ERRORLEVEL%"
echo [INFO] Exit code: %RC%
exit /b %RC%
