$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Project ".venv\Scripts\python.exe"

Write-Host "JARVIS v12.2 - INTERACTIVE MORNING RUNTIME FIX" -ForegroundColor Cyan
Write-Host ""
if (-not (Test-Path $Python)) { throw ".venv not found. Run Setup-Jarvis-Base.cmd first." }

$stop = Join-Path $Project "Stop-Jarvis.ps1"
if (Test-Path $stop) {
    Write-Host "Stopping previous Jarvis instance..." -ForegroundColor DarkGray
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $stop | Out-Host
}

Write-Host "Validating v12.2..." -ForegroundColor Cyan
Push-Location $Project
try {
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "v12.2 tests failed." }
} finally { Pop-Location }

Write-Host "Starting Jarvis with cache-safe UI..." -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project "Start-Jarvis-UI.ps1") -Page companion | Out-Host
Start-Sleep -Seconds 1
try {
    $ping = Invoke-RestMethod -Uri "http://127.0.0.1:4760/api/ping" -TimeoutSec 5
    if (-not $ping.ok) { throw "Jarvis UI did not answer." }
    Write-Host "Morning runtime online." -ForegroundColor Green
} catch { Write-Host "Jarvis started, but UI health check is still warming up." -ForegroundColor Yellow }

Write-Host ""
Write-Host "IMPORTANT: use the newly opened tab. The URL contains build=12.2 to bypass stale browser assets." -ForegroundColor Yellow
Write-Host "Test: Jarvis, faca meu briefing completo do dia." -ForegroundColor Green
