param(
    [ValidateSet("companion", "hq")]
    [string]$Page = "companion"
)

$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Project ".venv\Scripts\python.exe"
$DataDir = Join-Path $env:LOCALAPPDATA "JarvisNext"
$LockFile = Join-Path $DataDir "runtime\instance.lock"
$BaseUrl = "http://127.0.0.1:4760"
$TargetUrl = if ($Page -eq "hq") { "$BaseUrl/hq" } else { "$BaseUrl/" }

if (-not (Test-Path $Python)) {
    throw ".venv não encontrado. Execute Setup-Jarvis-Base.cmd primeiro."
}

function Test-JarvisUI {
    try {
        $ping = Invoke-RestMethod -Uri "$BaseUrl/api/ping" -Method Get -TimeoutSec 2
        return ($ping.ok -eq $true -and $ping.service -eq "jarvis-ui")
    } catch {
        return $false
    }
}

function Stop-LegacyJarvisIfNeeded {
    if (-not (Test-Path $LockFile)) { return }
    try {
        $lock = Get-Content $LockFile -Raw | ConvertFrom-Json
        $pidValue = [int]$lock.pid
    } catch {
        Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
        return
    }

    $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$pidValue" -ErrorAction SilentlyContinue
    if (-not $proc) {
        Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
        return
    }

    $cmd = [string]$proc.CommandLine
    if ($cmd -match "(?i)(-m\s+jarvis|jarvis\\__main__|Sind-AI)") {
        Write-Host "Encontrada instância antiga do Jarvis (PID $pidValue) sem servidor de UI." -ForegroundColor Yellow
        Write-Host "Migrando para a instância unificada..." -ForegroundColor Yellow
        Stop-Process -Id $pidValue -Force
        for ($i=0; $i -lt 20; $i++) {
            Start-Sleep -Milliseconds 250
            if (-not (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) { break }
        }
        if (-not (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) {
            Remove-Item $LockFile -Force -ErrorAction SilentlyContinue
        }
        return
    }

    throw "O lock pertence ao PID $pidValue e não foi possível confirmar que é um processo Jarvis. Não vou encerrá-lo automaticamente."
}

if (Test-JarvisUI) {
    Start-Process $TargetUrl
    exit 0
}

Stop-LegacyJarvisIfNeeded

Write-Host "Iniciando instância unificada do Jarvis..." -ForegroundColor Cyan
$proc = Start-Process -FilePath $Python -ArgumentList @("-m", "jarvis", "ui", "--no-open") -WorkingDirectory $Project -PassThru

$ready = $false
for ($i=0; $i -lt 120; $i++) {
    Start-Sleep -Milliseconds 250
    if (Test-JarvisUI) { $ready = $true; break }
    if ($proc.HasExited) { break }
}

if (-not $ready) {
    throw "Jarvis não abriu o servidor local em $BaseUrl. Execute Validate-Jarvis-Base.cmd para diagnóstico."
}

Start-Process $TargetUrl
Write-Host "Jarvis ativo: $TargetUrl" -ForegroundColor Green
