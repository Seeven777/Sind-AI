$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Project

$Python = Join-Path $Project ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw ".venv não encontrado. Execute primeiro Setup-Jarvis-Phase0.cmd."
}

Write-Host ""
Write-Host "JARVIS NEXT - PHASE 0 VALIDATION" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor DarkCyan

Write-Host "`n[1/3] Testes..."
& $Python -m pytest
if ($LASTEXITCODE -ne 0) { throw "Testes falharam." }

Write-Host "`n[2/3] Smoke boot..."
$Smoke = Join-Path $env:TEMP ("JarvisNext-Validate-" + [guid]::NewGuid().ToString("N"))
try {
    & $Python -m jarvis --data-dir $Smoke --once
    if ($LASTEXITCODE -ne 0) { throw "Smoke boot falhou." }
} finally {
    Remove-Item $Smoke -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host "`n[3/3] Git status..."
& git status --short

Write-Host ""
Write-Host "VALIDAÇÃO CONCLUÍDA." -ForegroundColor Green
