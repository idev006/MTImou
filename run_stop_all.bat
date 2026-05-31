@echo off
setlocal

echo [INFO] Stopping stale viewer/tunnel processes...
for /f "skip=1 tokens=2 delims==" %%P in ('wmic process where "name='python.exe' and (CommandLine like '%%imou_ffplay_viewer.py%%' or CommandLine like '%%imou_opencv_spike.py%%' or CommandLine like '%%dh-p2p\\main.py%%')" get ProcessId /value 2^>nul') do (
  if not "%%P"=="" (
    echo [INFO] Kill python PID %%P
    taskkill /PID %%P /T /F >nul 2>&1
  )
)

taskkill /IM ffplay.exe /T /F >nul 2>&1
taskkill /IM ffprobe.exe /T /F >nul 2>&1

for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":554 .*LISTENING"') do (
  echo [INFO] Port 554 held by PID %%P, killing...
  taskkill /PID %%P /T /F >nul 2>&1
)

echo [INFO] Done.
endlocal
exit /b 0

