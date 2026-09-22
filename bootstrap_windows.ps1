param([switch]$SkipModels)
$ErrorActionPreference='Stop'
$installer = Join-Path $PSScriptRoot 'vercel_portal\Install-Jarvis.ps1'
if (-not (Test-Path $installer)) { throw 'Install-Jarvis.ps1 nao encontrado.' }
& powershell -ExecutionPolicy Bypass -File $installer -InstallDir $PSScriptRoot -SkipModels:$SkipModels -NoLaunch
