$ErrorActionPreference = "Stop"
$DataDir = Join-Path $env:LOCALAPPDATA "JarvisNext"
$LockFile = Join-Path $DataDir "runtime\instance.lock"

if (-not (Test-Path $LockFile)) {
    Write-Host "Nenhuma instância do Jarvis registrada." -ForegroundColor Yellow
    exit 0
}

try {
    $lock = Get-Content $LockFile -Raw | ConvertFrom-Json
    $pidValue = [int]$lock.pid
} catch {
    Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
    Write-Host "Lock inválido removido." -ForegroundColor Yellow
    exit 0
}

$proc = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction SilentlyContinue
if (-not $proc) {
    Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
    Write-Host "Lock órfão removido." -ForegroundColor Yellow
    exit 0
}

$cmd = [string]$proc.CommandLine
if ($cmd -notmatch "(?i)(-m\s+jarvis|jarvis\\__main__|Sind-AI)") {
    throw "PID $pidValue não parece pertencer ao Jarvis. Nenhum processo foi encerrado."
}

Stop-Process -Id $pidValue -Force
Start-Sleep -Milliseconds 500
Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
Write-Host "Jarvis encerrado (PID $pidValue)." -ForegroundColor Green
