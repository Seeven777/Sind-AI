$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Project
$Python = Join-Path $Project ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw ".venv não encontrado." }

Write-Host "JARVIS NEXT 1.0 RC2 - BASE VALIDATION" -ForegroundColor Cyan

$StopScript = Join-Path $Project "Stop-Jarvis.ps1"
if (Test-Path $StopScript) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StopScript
}

Write-Host "`n[1/8] Testes..."
& $Python -m pytest
if ($LASTEXITCODE -ne 0) { throw "Testes falharam." }

Write-Host "`n[2/8] Doctor..."
& $Python -m jarvis doctor
if ($LASTEXITCODE -ne 0) { throw "Doctor falhou." }

Write-Host "`n[3/8] Model probe..."
& $Python -m jarvis model-probe
if ($LASTEXITCODE -ne 0) { throw "Model probe falhou." }

Write-Host "`n[4/8] Connectors..."
& $Python -m jarvis sync
if ($LASTEXITCODE -ne 0) { throw "Connector sync falhou." }

Write-Host "`n[5/8] Inbox Agent..."
& $Python -m jarvis inbox
if ($LASTEXITCODE -ne 0) { throw "Inbox Agent falhou." }

Write-Host "`n[6/8] Briefing..."
& $Python -m jarvis briefing
if ($LASTEXITCODE -ne 0) { throw "Briefing falhou." }

Write-Host "`n[7/8] Research Agent..."
& $Python -m jarvis demo-agent --prompt "Pesquise em poucas linhas como um agente deve entregar evidências do próprio trabalho."
if ($LASTEXITCODE -ne 0) { throw "Research Agent falhou." }

Write-Host "`n[8/8] HQ contract..."
$hqJson = & $Python -m jarvis hq
if ($LASTEXITCODE -ne 0) { throw "HQ snapshot falhou." }
if (($hqJson | Out-String) -notmatch "jarvis.hq.snapshot.v2") { throw "Contrato HQ v2 não encontrado." }
Write-Host "HQ snapshot v2: PASS" -ForegroundColor Green

Write-Host "`nVALIDAÇÃO CONCLUÍDA." -ForegroundColor Green
