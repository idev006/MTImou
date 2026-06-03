@echo off
setlocal
cd /d "%~dp0"
call "%~dp0set_python_utf8_env.bat"
call "%~dp0run_camera_stable.bat" cam1
exit /b %ERRORLEVEL%
