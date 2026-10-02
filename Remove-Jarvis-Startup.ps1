$ErrorActionPreference = "Stop"
$TaskName = "Jarvis Next"
& schtasks.exe /Delete /TN $TaskName /F 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Inicialização automática removida." -ForegroundColor Green
} else {
    Write-Host "A tarefa não existia ou já havia sido removida."
}
