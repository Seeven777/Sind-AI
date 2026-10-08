$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$DataDir = Join-Path $env:LOCALAPPDATA 'JarvisNext'
$Secret = Join-Path $DataDir 'secrets\mobile_access_token.bin'

Write-Host 'Rotacionando a credencial de acesso remoto do Jarvis...' -ForegroundColor Cyan
try { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project 'Disable-Jarvis-Anywhere.ps1') | Out-Null } catch {}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project 'Stop-Jarvis.ps1') | Out-Null
Start-Sleep -Milliseconds 800
Remove-Item $Secret -Force -ErrorAction SilentlyContinue
Write-Host 'Token anterior invalidado.' -ForegroundColor Green
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project 'Enable-Jarvis-Anywhere.ps1')
