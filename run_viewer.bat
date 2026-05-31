@echo off
setlocal

cd /d "%~dp0"

echo [INFO] Default viewer is ffplay-based (more stable for live watching).
echo [INFO] For OpenCV viewer, use run_viewer_opencv.bat
call "%~dp0run_viewer_ffplay.bat"
exit /b %ERRORLEVEL%
