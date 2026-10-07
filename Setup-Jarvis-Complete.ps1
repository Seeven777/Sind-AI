param(
    [switch]$SkipModelPull,
    [switch]$SkipAgentModels
)
$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "JARVIS NEXT PRESENCE v5 - INSTALACAO COMPLETA" -ForegroundColor Cyan
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

if (-not $SkipAgentModels -and -not $SkipModelPull) {
    $agentModels = Join-Path $Project "Install-Jarvis-Agent-Models.ps1"
    if (Test-Path $agentModels) {
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $agentModels
        if ($LASTEXITCODE -ne 0) { throw "Instalação dos modelos especializados falhou." }
    }
}

Write-Host ""
Write-Host "Instalação completa concluída." -ForegroundColor Green
Write-Host "Voz: ElevenLabs/Piper são opcionais; Windows SAPI e Web Speech funcionam como fallback sem configuração."
Write-Host "Google está implementado, mas requer google_client.json e sua autorização OAuth."
Write-Host ""
Write-Host "Execute Validate-Jarvis-Complete.cmd para validar o ambiente."
