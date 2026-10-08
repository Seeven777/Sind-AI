$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Project ".venv\Scripts\python.exe"

Write-Host "JARVIS v9 - PERFORMANCE" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $Python)) {
    throw ".venv not found. Run Setup-Jarvis-Base.cmd first."
}

$stop = Join-Path $Project "Stop-Jarvis.ps1"
if (Test-Path $stop) {
    Write-Host "Stopping previous Jarvis instance..." -ForegroundColor DarkGray
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $stop | Out-Host
}

Write-Host "Running v9 validation..." -ForegroundColor Cyan
Push-Location $Project
try {
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "v9 tests failed." }
} finally {
    Pop-Location
}

Write-Host "Starting Jarvis v9..." -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project "Start-Jarvis-UI.ps1") -Page companion | Out-Host
Start-Sleep -Seconds 1

try {
    $perf = Invoke-RestMethod -Uri "http://127.0.0.1:4760/api/performance" -TimeoutSec 5
    Write-Host "Performance monitor active." -ForegroundColor Green
    Write-Host "Samples: $($perf.samples)" -ForegroundColor DarkGray
} catch {
    Write-Host "Jarvis started, but performance diagnostics were not readable yet." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "v9 active. Jarvis Anywhere v8 remains compatible." -ForegroundColor Green
