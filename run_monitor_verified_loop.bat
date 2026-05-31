@echo off
setlocal EnableDelayedExpansion

cd /d "%~dp0"

if exist "camera.env.bat" (
  call "camera.env.bat"
)

if "%IMOU_MONITOR_RUNS%"=="" set "IMOU_MONITOR_RUNS=12"
if "%IMOU_MONITOR_INTERVAL_SEC%"=="" set "IMOU_MONITOR_INTERVAL_SEC=8"
if "%IMOU_FFPLAY_VERIFY_SEC%"=="" set "IMOU_FFPLAY_VERIFY_SEC=5"
if "%IMOU_FFPLAY_AUTOEXIT_SEC%"=="" set "IMOU_FFPLAY_AUTOEXIT_SEC=15"
if "%IMOU_SKIP_PROBE_ON_FFPLAY%"=="" set "IMOU_SKIP_PROBE_ON_FFPLAY=1"
if "%IMOU_RTSP_SUBTYPE%"=="" set "IMOU_RTSP_SUBTYPE=0"
if "%IMOU_MONITOR_LOGS_DIR%"=="" set "IMOU_MONITOR_LOGS_DIR=%~dp0logs"

if not exist "%IMOU_MONITOR_LOGS_DIR%" mkdir "%IMOU_MONITOR_LOGS_DIR%"

set "TS=%date:~10,4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%%time:~6,2%"
set "TS=%TS: =0%"
set "SUMMARY=%IMOU_MONITOR_LOGS_DIR%\verified_monitor_loop_%TS%.log"
set /a OK=0

echo [INFO] Monitor loop runs=%IMOU_MONITOR_RUNS% interval=%IMOU_MONITOR_INTERVAL_SEC%s
echo [INFO] Summary log: %SUMMARY%

for /L %%I in (1,1,%IMOU_MONITOR_RUNS%) do (
  set "RUNLOG=%IMOU_MONITOR_LOGS_DIR%\verified_loop_run_%TS%_%%I.log"
  echo [INFO] Run %%I/%IMOU_MONITOR_RUNS% starting...
  call .\run_stop_all.bat >nul 2>&1
  call .\run_viewer_verified.bat %IMOU_RTSP_SUBTYPE% > "!RUNLOG!" 2>&1
  set "RC=!ERRORLEVEL!"
  findstr /C:"[SUCCESS] Verified stream on:" "!RUNLOG!" >nul
  if !ERRORLEVEL! EQU 0 if "!RC!"=="0" (
    set /a OK+=1
    echo [RESULT] run=%%I status=SUCCESS rc=!RC! log=!RUNLOG!
    >> "%SUMMARY%" echo [RESULT] run=%%I status=SUCCESS rc=!RC! log=!RUNLOG!
  ) else (
    echo [RESULT] run=%%I status=FAIL rc=!RC! log=!RUNLOG!
    >> "%SUMMARY%" echo [RESULT] run=%%I status=FAIL rc=!RC! log=!RUNLOG!
  )
  if %%I LSS %IMOU_MONITOR_RUNS% timeout /t %IMOU_MONITOR_INTERVAL_SEC% /nobreak >nul
)

set /a TOTAL=%IMOU_MONITOR_RUNS%
set /a RATE=OK*100/TOTAL
echo [SUMMARY] success=%OK%/%TOTAL% (%RATE%%)
>> "%SUMMARY%" echo [SUMMARY] success=%OK%/%TOTAL% (%RATE%%)

if %OK% EQU %TOTAL% (
  exit /b 0
) else (
  exit /b 1
)

