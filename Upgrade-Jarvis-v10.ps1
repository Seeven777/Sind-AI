$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Project ".venv\Scripts\python.exe"

Write-Host "JARVIS v10 - EVOLUTION LAB" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $Python)) {
    throw ".venv not found. Run Setup-Jarvis-Base.cmd first."
}

$stop = Join-Path $Project "Stop-Jarvis.ps1"
if (Test-Path $stop) {
    Write-Host "Stopping previous Jarvis instance..." -ForegroundColor DarkGray
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $stop | Out-Host
}

Write-Host "Running v10 validation..." -ForegroundColor Cyan
Push-Location $Project
try {
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "v10 tests failed." }
} finally {
    Pop-Location
}

Write-Host "Starting Jarvis v10..." -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project "Start-Jarvis-UI.ps1") -Page companion | Out-Host
Start-Sleep -Seconds 1

try {
    $auto = Invoke-RestMethod -Uri "http://127.0.0.1:4760/api/autonomy" -TimeoutSec 5
    Write-Host "Autonomy online. Pending improvements: $($auto.stats.pending_improvements)" -ForegroundColor Green
} catch {
    Write-Host "Jarvis started, but autonomy diagnostics were not readable yet." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "v10 active. Self-improvements now use an isolated tested sandbox before promotion." -ForegroundColor Green
Write-Host "Jarvis Anywhere/ngrok from v8/v9 remains unchanged." -ForegroundColor DarkGray
