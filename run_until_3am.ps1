param(
    [string]$Workspace = "F:\programming\python\MTImou"
)

$ErrorActionPreference = "Stop"

Set-Location $Workspace

$logsDir = Join-Path $Workspace "logs"
if (!(Test-Path $logsDir)) {
    New-Item -ItemType Directory -Path $logsDir | Out-Null
}

$runnerLog = Join-Path $logsDir "overnight_runner.log"

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    $line | Tee-Object -FilePath $runnerLog -Append
}

$now = Get-Date
$cutoff = Get-Date -Hour 3 -Minute 0 -Second 0
if ($now -ge $cutoff) {
    $cutoff = $cutoff.AddDays(1)
}

Write-Log "Overnight runner started. Cutoff: $($cutoff.ToString('yyyy-MM-dd HH:mm:ss'))"

$attempt = 0
$success = $false

while ((Get-Date) -lt $cutoff) {
    $attempt++
    Write-Log "Attempt ${attempt}: run_free_dhp2p_auto.bat"

    $env:IMOU_RELAY_ATTEMPTS = "1"
    $env:IMOU_PROBE_TIMEOUT_SEC = "4"
    $env:IMOU_FRAME_WAIT_SEC = "5"

    & "$Workspace\run_free_dhp2p_auto.bat" *>> $runnerLog
    $rc = $LASTEXITCODE
    Write-Log "Attempt ${attempt} finished with code $rc"

    if ($rc -eq 0) {
        $success = $true
        Write-Log "SUCCESS detected. Stop retry loop."
        break
    }

    Start-Sleep -Seconds 20
}

if (-not $success) {
    Write-Log "Cutoff reached or no success before cutoff."
}

if ((Get-Date) -ge $cutoff) {
    Write-Log "Cutoff time reached. Shutting down now."
    shutdown /s /t 0
} else {
    Write-Log "Runner ended before cutoff (success or manual stop)."
}
