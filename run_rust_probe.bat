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
if "%IMOU_TUNNEL_MODE%"=="" set "IMOU_TUNNEL_MODE=auto"
if "%IMOU_RUST_READY_TIMEOUT_SEC%"=="" set "IMOU_RUST_READY_TIMEOUT_SEC=60"

if "%IMOU_CAMERA_SN%"=="" (
  set /p IMOU_CAMERA_SN=Enter IMOU_CAMERA_SN: 
)
if "%IMOU_CAMERA_PASSWORD%"=="" (
  set /p IMOU_CAMERA_PASSWORD=Enter IMOU_CAMERA_PASSWORD: 
)

for %%L in (1554 17554 18554 19554 20554) do (
  for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":%%L .*LISTENING"') do (
    echo [INFO] Port %%L in use by PID %%P, terminating...
    taskkill /PID %%P /F >nul 2>&1
  )
)

echo [INFO] Ensure Rust build exists...
if not exist "%DH_P2P_REPO_DIR%\target\release\dh-p2p.exe" (
  if exist "%USERPROFILE%\.cargo\bin\cargo.exe" (
    pushd "%DH_P2P_REPO_DIR%"
    "%USERPROFILE%\.cargo\bin\cargo.exe" build --release
    set "BUILD_RC=%ERRORLEVEL%"
    popd
    if not "%BUILD_RC%"=="0" exit /b %BUILD_RC%
  ) else (
    echo [ERROR] cargo.exe not found. Install Rust first.
    exit /b 1
  )
)

echo [INFO] Running Rust ffprobe test...
"%PYTHON_EXE%" -u src\rust_ffprobe_test.py
set "RC=%ERRORLEVEL%"
echo [INFO] Exit code: %RC%
exit /b %RC%
