$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Script = Join-Path $Project "Start-Jarvis-Background.ps1"
$TaskName = "Jarvis Next"

if (-not (Test-Path $Script)) { throw "Start-Jarvis-Background.ps1 não encontrado." }

$action = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$Script`""
& schtasks.exe /Create /TN $TaskName /SC ONLOGON /TR $action /F
if ($LASTEXITCODE -ne 0) { throw "Falha ao registrar tarefa de inicialização." }

Write-Host "Jarvis configurado para iniciar com o Windows." -ForegroundColor Green
Write-Host "Task Scheduler: $TaskName"
