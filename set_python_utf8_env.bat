@echo off
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "MTIMOU_LOCAL_ENV=%~dp0camera.env.bat"
if exist "%MTIMOU_LOCAL_ENV%" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$path = [System.IO.Path]::GetFullPath('%MTIMOU_LOCAL_ENV%'); $bytes = [System.IO.File]::ReadAllBytes($path); if ($bytes.Length -ge 3 -and $bytes[0] -eq 239 -and $bytes[1] -eq 187 -and $bytes[2] -eq 191) { $trimmed = if ($bytes.Length -gt 3) { $bytes[3..($bytes.Length - 1)] } else { [byte[]]::new(0) }; [System.IO.File]::WriteAllBytes($path, $trimmed); Write-Host '[INFO] Removed UTF-8 BOM from camera.env.bat'; }"
)
set "MTIMOU_LOCAL_ENV="
