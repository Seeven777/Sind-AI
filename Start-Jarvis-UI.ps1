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

$StartupLogDir = Join-Path $DataDir "logs"
New-Item -ItemType Directory -Path $StartupLogDir -Force | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$StdoutLog = Join-Path $StartupLogDir "startup-$Stamp.out.log"
$StderrLog = Join-Path $StartupLogDir "startup-$Stamp.err.log"

Write-Host "Iniciando instância unificada do Jarvis..." -ForegroundColor Cyan
$proc = Start-Process -FilePath $Python -ArgumentList @("-m", "jarvis", "ui", "--no-open", "--mobile") -WorkingDirectory $Project -RedirectStandardOutput $StdoutLog -RedirectStandardError $StderrLog -WindowStyle Hidden -PassThru

$ready = $false
for ($i=0; $i -lt 240; $i++) {
    Start-Sleep -Milliseconds 250
    if (Test-JarvisUI) { $ready = $true; break }
    if ($proc.HasExited) { break }
}

if (-not $ready) {
    Write-Host "`nJarvis não ficou disponível em $BaseUrl dentro do tempo esperado." -ForegroundColor Red
    Write-Host "PID: $($proc.Id) | Encerrado: $($proc.HasExited)" -ForegroundColor Yellow
    Write-Host "Log stdout: $StdoutLog" -ForegroundColor DarkGray
    Write-Host "Log stderr: $StderrLog" -ForegroundColor DarkGray
    if (Test-Path $StderrLog) {
        $err = Get-Content $StderrLog -Tail 80 -ErrorAction SilentlyContinue
        if ($err) {
            Write-Host "`n--- STDERR ---" -ForegroundColor Yellow
            $err | ForEach-Object { Write-Host $_ }
        }
    }
    if (Test-Path $StdoutLog) {
        $out = Get-Content $StdoutLog -Tail 40 -ErrorAction SilentlyContinue
        if ($out) {
            Write-Host "`n--- STDOUT ---" -ForegroundColor Yellow
            $out | ForEach-Object { Write-Host $_ }
        }
    }
    if ($proc.HasExited) {
        throw "Jarvis encerrou durante a inicialização. Consulte os logs acima."
    }
    throw "Jarvis não abriu o servidor local em $BaseUrl dentro do tempo esperado."
}

Start-Process $TargetUrl
Write-Host "Jarvis ativo: $TargetUrl" -ForegroundColor Green
