$ErrorActionPreference = 'Stop'
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Project

Write-Host 'JARVIS v7 — Premium UI + Anywhere' -ForegroundColor Cyan
Write-Host 'Encerrando instância anterior...' -ForegroundColor Gray
try { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project 'Stop-Jarvis.ps1') | Out-Host } catch {}
Start-Sleep -Milliseconds 700

Write-Host 'Iniciando Jarvis com acesso mobile/remoto protegido...' -ForegroundColor Gray
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project 'Start-Jarvis-UI.ps1') -Page companion | Out-Host

Write-Host ''
Write-Host 'v7 ativa.' -ForegroundColor Green
Write-Host 'Para acessar de QUALQUER rede/dispositivo sem instalar app no cliente:' -ForegroundColor White
Write-Host '  Enable-Jarvis-Anywhere.cmd' -ForegroundColor Cyan
Write-Host ''
Write-Host 'A exposição pública não é ligada silenciosamente: execute o comando acima uma vez para autorizar o Funnel.' -ForegroundColor DarkGray
