$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host 'Recriando o Jarvis Anywhere de forma simples...' -ForegroundColor Cyan
try { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project 'Disable-Jarvis-Anywhere.ps1') | Out-Null } catch {}
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project 'Enable-Jarvis-Anywhere.ps1')
exit $LASTEXITCODE
