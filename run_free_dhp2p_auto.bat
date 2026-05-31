@echo off
setlocal

cd /d "%~dp0"

if exist "camera.env.bat" (
  call "camera.env.bat"
) else (
  echo [ERROR] Missing camera.env.bat
  exit /b 1
)

set IMOU_SKIP_CAMERA_ENV=1
if "%IMOU_PROBE_TIMEOUT_SEC%"=="" set IMOU_PROBE_TIMEOUT_SEC=5
if "%IMOU_FRAME_WAIT_SEC%"=="" set IMOU_FRAME_WAIT_SEC=6

echo [INFO] Free mode test #1: relay mode
set IMOU_FORCE_RELAY=1
if "%IMOU_RELAY_ATTEMPTS%"=="" set IMOU_RELAY_ATTEMPTS=3
call "%~dp0run_relay_test.bat"
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" (
  echo [SUCCESS] Free relay mode works.
  exit /b 0
)

echo [WARN] Relay mode failed, trying direct mode...
set IMOU_FORCE_RELAY=0
set IMOU_RELAY_ATTEMPTS=2
call "%~dp0run_relay_test.bat"
set "RC=%ERRORLEVEL%"
if "%RC%"=="0" (
  echo [SUCCESS] Free direct mode works.
  exit /b 0
)

echo [ERROR] Free dh-p2p auto mode failed in both relay and direct.
exit /b %RC%
