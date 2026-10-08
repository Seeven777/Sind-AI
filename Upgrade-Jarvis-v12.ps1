$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Project ".venv\Scripts\python.exe"

Write-Host "JARVIS v12 - MORNING PRESENCE" -ForegroundColor Cyan
Write-Host ""
if (-not (Test-Path $Python)) { throw ".venv not found. Run Setup-Jarvis-Base.cmd first." }

$stop = Join-Path $Project "Stop-Jarvis.ps1"
if (Test-Path $stop) {
    Write-Host "Stopping previous Jarvis instance..." -ForegroundColor DarkGray
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $stop | Out-Host
}

Write-Host "Checking browser runtime for task integration..." -ForegroundColor Cyan
& $Python -c "import playwright" 2>$null
if ($LASTEXITCODE -ne 0) {
    & $Python -m pip install "playwright>=1.50"
}
# Browser installation is idempotent; Playwright skips already installed binaries.
& $Python -m playwright install chromium
if ($LASTEXITCODE -ne 0) { Write-Host "Chromium could not be prepared. Morning briefing still works; task connector will need Setup-Jarvis-Extras.cmd." -ForegroundColor Yellow }

Write-Host "Running v12 validation..." -ForegroundColor Cyan
Push-Location $Project
try {
    & $Python -m pytest -q
    if ($LASTEXITCODE -ne 0) { throw "v12 tests failed." }
} finally { Pop-Location }

Write-Host "Starting Jarvis v12..." -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project "Start-Jarvis-UI.ps1") -Page companion | Out-Host
Start-Sleep -Seconds 1
try {
    $ping = Invoke-RestMethod -Uri "http://127.0.0.1:4760/api/ping" -TimeoutSec 5
    if (-not $ping.ok) { throw "Jarvis UI did not answer." }
    Write-Host "Morning Presence online." -ForegroundColor Green
} catch { Write-Host "Jarvis started, but UI health check is still warming up." -ForegroundColor Yellow }

Write-Host ""
Write-Host "v12 active: boot/wake animation, weather, news and responsibilities sequence." -ForegroundColor Green
Write-Host "For the marketing task organizer, run Connect-Marketing-Tasks.cmd once." -ForegroundColor Yellow
Write-Host "Credentials are stored locally with Windows DPAPI and are not embedded in Jarvis source files." -ForegroundColor DarkGray
