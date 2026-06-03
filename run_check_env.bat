@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"
call "%~dp0set_python_utf8_env.bat"

if exist "camera.env.bat" (
  call "camera.env.bat"
) else (
  echo [WARN] camera.env.bat not found.
)

set "USERNAME=%IMOU_CAMERA_USERNAME%"
set "PASSWORD=%IMOU_CAMERA_PASSWORD%"
set "SN=%IMOU_CAMERA_SN%"
set "TYPE=%IMOU_CAMERA_TYPE%"
set "FORCE_RELAY=%IMOU_FORCE_RELAY%"
set "SUBTYPE=%IMOU_RTSP_SUBTYPE%"
set "HOST=%IMOU_RTSP_HOST%"
set "PORT=%IMOU_RTSP_PORT%"
set "CHANNEL=%IMOU_RTSP_CHANNEL%"
set "REPO_DIR=%DH_P2P_REPO_DIR%"
set "FFMPEG_BIN=%FFMPEG_BIN_DIR%"

set "MASKED_PASSWORD=(missing)"
if not "!PASSWORD!"=="" (
  set "PFX=!PASSWORD:~0,2!"
  set "SFX=!PASSWORD:~-2!"
  if "!PASSWORD:~2,1!"=="" (
    set "MASKED_PASSWORD=**"
  ) else (
    set "MASKED_PASSWORD=!PFX!****!SFX!"
  )
)

set "MASKED_SN=(missing)"
if not "!SN!"=="" (
  set "SN_LEN_TEST=!SN:~4,1!"
  if "!SN_LEN_TEST!"=="" (
    set "MASKED_SN=****"
  ) else (
    set "MASKED_SN=!SN:~0,4!****!SN:~-4!"
  )
)

if "%USERNAME%"=="" set "USERNAME=(missing)"
if "%TYPE%"=="" set "TYPE=(missing)"
if "%FORCE_RELAY%"=="" set "FORCE_RELAY=(missing)"
if "%SUBTYPE%"=="" set "SUBTYPE=(missing)"
if "%HOST%"=="" set "HOST=(missing)"
if "%PORT%"=="" set "PORT=(missing)"
if "%CHANNEL%"=="" set "CHANNEL=(missing)"
if "%REPO_DIR%"=="" set "REPO_DIR=(missing)"
if "%FFMPEG_BIN%"=="" set "FFMPEG_BIN=(missing)"

echo [CHECK] IMOU_CAMERA_USERNAME=%USERNAME%
echo [CHECK] IMOU_CAMERA_PASSWORD=%MASKED_PASSWORD%
echo [CHECK] IMOU_CAMERA_SN=%MASKED_SN%
echo [CHECK] IMOU_CAMERA_TYPE=%TYPE%
echo [CHECK] IMOU_FORCE_RELAY=%FORCE_RELAY%
echo [CHECK] IMOU_RTSP_SUBTYPE=%SUBTYPE%
echo [CHECK] IMOU_RTSP_HOST=%HOST%
echo [CHECK] IMOU_RTSP_PORT=%PORT%
echo [CHECK] IMOU_RTSP_CHANNEL=%CHANNEL%
echo [CHECK] DH_P2P_REPO_DIR=%REPO_DIR%
echo [CHECK] FFMPEG_BIN_DIR=%FFMPEG_BIN%

if exist ".venv\Scripts\python.exe" (
  echo [CHECK] PYTHON_EXE=%~dp0.venv\Scripts\python.exe
  "%~dp0.venv\Scripts\python.exe" --version
) else (
  echo [WARN] .venv\Scripts\python.exe not found.
)

endlocal
exit /b 0
