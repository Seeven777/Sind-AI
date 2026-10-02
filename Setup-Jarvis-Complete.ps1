param(
    [switch]$SkipModelPull
)
$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "JARVIS NEXT 1.0 RC2 - INSTALACAO COMPLETA" -ForegroundColor Cyan
Write-Host ""

$base = Join-Path $Project "Setup-Jarvis-Base.ps1"
$extras = Join-Path $Project "Setup-Jarvis-Extras.ps1"

if ($SkipModelPull) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $base -SkipModelPull -SkipAgentDemo
} else {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $base
}
if ($LASTEXITCODE -ne 0) { throw "Instalação base falhou." }

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $extras
if ($LASTEXITCODE -ne 0) { throw "Instalação de Computer Use falhou." }

Write-Host ""
Write-Host "Instalação completa concluída." -ForegroundColor Green
Write-Host "Voz local está implementada, mas requer binários/modelos Piper e whisper.cpp configurados."
Write-Host "Google está implementado, mas requer google_client.json e sua autorização OAuth."
Write-Host ""
Write-Host "Execute Validate-Jarvis-Complete.cmd para validar o ambiente."
