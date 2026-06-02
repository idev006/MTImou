@echo off
setlocal
cd /d "%~dp0"

set "BOOTSTRAP_PY="

if defined IMOU_BOOTSTRAP_PYTHON if exist "%IMOU_BOOTSTRAP_PYTHON%" (
  set "BOOTSTRAP_PY=%IMOU_BOOTSTRAP_PYTHON%"
)

if not defined BOOTSTRAP_PY (
  py -3.12 -c "import sys; print(sys.executable)" > "%TEMP%\mtimou_py312_path.txt" 2>nul
  if not errorlevel 1 (
    set /p BOOTSTRAP_PY=<"%TEMP%\mtimou_py312_path.txt"
    del "%TEMP%\mtimou_py312_path.txt" >nul 2>nul
  )
)

if not defined BOOTSTRAP_PY (
  python -c "import sys; print(sys.executable)" > "%TEMP%\mtimou_python_path.txt" 2>nul
  if not errorlevel 1 (
    set /p BOOTSTRAP_PY=<"%TEMP%\mtimou_python_path.txt"
    del "%TEMP%\mtimou_python_path.txt" >nul 2>nul
  )
)

if not defined BOOTSTRAP_PY (
  echo [ERROR] Python 3.12 was not found.
  echo [INFO] Install Python 3.12, or set IMOU_BOOTSTRAP_PYTHON to your python.exe path.
  exit /b 101
)

echo [INFO] Bootstrap Python: %BOOTSTRAP_PY%

if not exist ".venv\Scripts\python.exe" (
  echo [INFO] Creating .venv ...
  "%BOOTSTRAP_PY%" -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv
    exit /b 102
  )
) else (
  echo [INFO] Reusing existing .venv
)

set "PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] Missing venv python after setup: %PY%
  exit /b 103
)

echo [INFO] Upgrading pip ...
"%PY%" -m pip install --upgrade pip
if errorlevel 1 (
  echo [ERROR] Failed to upgrade pip
  exit /b 104
)

echo [INFO] Installing project dependencies ...
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Failed to install requirements.txt
  exit /b 105
)

if not exist "camera.env.bat" if exist "camera.env.bat.example" (
  copy /y "camera.env.bat.example" "camera.env.bat" >nul
  echo [INFO] Created camera.env.bat from camera.env.bat.example
)

if not exist "camera_presets.json" if exist "camera_presets.example.json" (
  copy /y "camera_presets.example.json" "camera_presets.json" >nul
  echo [INFO] Created camera_presets.json from camera_presets.example.json
)

if not exist "logs" mkdir "logs" >nul 2>nul

echo [INFO] Setup completed.
echo [INFO] Next steps:
echo        1. Edit camera.env.bat if needed
echo        2. Review cameras.json
echo        3. Run run_doctor.bat
echo        4. Run run_control_panel.bat
exit /b 0
