$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Project ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw ".venv não encontrado. Execute Setup-Jarvis-Base.cmd primeiro."
}
Set-Location $Project

Write-Host "JARVIS NEXT - EXTRAS DE COMPUTER USE" -ForegroundColor Cyan
Write-Host ""
Write-Host "Instalando Playwright e Windows UI Automation..."

& $Python -m pip install -e ".[desktop]"
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependências desktop." }

Write-Host "Instalando Chromium gerenciado pelo Playwright..."
& $Python -m playwright install chromium
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar Chromium." }

Write-Host ""
Write-Host "Browser estruturado: instalado" -ForegroundColor Green
Write-Host "Windows UI Automation: instalada" -ForegroundColor Green
Write-Host ""
& $Python -m jarvis browser-doctor
& $Python -m jarvis windows-doctor
