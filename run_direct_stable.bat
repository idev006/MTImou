@echo off
setlocal
cd /d "%~dp0"
call "%~dp0run_camera_stable.bat" cam1
exit /b %ERRORLEVEL%
