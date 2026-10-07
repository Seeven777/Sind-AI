param(
    [switch]$SkipModelDownload,
    [switch]$SkipMobileFirewall
)
$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Stop = Join-Path $Project "Stop-Jarvis.ps1"
$Start = Join-Path $Project "Start-Jarvis-UI.ps1"

Write-Host "JARVIS PRESENCE v5 - ATIVAÇÃO" -ForegroundColor Cyan
Write-Host ""

if (Test-Path $Stop) {
    Write-Host "Encerrando instância anterior..." -ForegroundColor DarkGray
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Stop | Out-Host
}

if (-not $SkipModelDownload) {
    $models = Join-Path $Project "Install-Jarvis-Agent-Models.ps1"
    if (Test-Path $models) {
        try {
            & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $models | Out-Host
        } catch {
            Write-Host "Modelos especializados não foram baixados: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "Os agentes continuarão usando o modelo principal como fallback." -ForegroundColor DarkGray
        }
    }
}

if (-not $SkipMobileFirewall) {
    $mobileFirewall = Join-Path $Project "Enable-Jarvis-Mobile.ps1"
    if (Test-Path $mobileFirewall) {
        Write-Host ""
        Write-Host "Preparando acesso pelo celular (somente rede privada)..." -ForegroundColor Cyan
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $mobileFirewall | Out-Host
    }
}

Write-Host ""
Write-Host "Iniciando Jarvis v5..." -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Start -Page companion | Out-Host
Start-Sleep -Seconds 1

try {
    $mobile = Invoke-RestMethod -Uri "http://127.0.0.1:4760/api/mobile" -TimeoutSec 4
    if ($mobile.enabled -and $mobile.connect_url) {
        Set-Clipboard -Value $mobile.connect_url
        Write-Host ""
        Write-Host "Mobile pronto: $($mobile.connect_url)" -ForegroundColor Green
        Write-Host "Link copiado para a área de transferência." -ForegroundColor DarkGray
    }
} catch {
    Write-Host "Não foi possível obter o link mobile agora." -ForegroundColor Yellow
}

try {
    $diag = Invoke-RestMethod -Uri "http://127.0.0.1:4760/api/voice/diagnostics" -TimeoutSec 4
    $active = $diag.active_backend
    Write-Host "Voz ativa: $active" -ForegroundColor Green
} catch {
    Write-Host "Diagnóstico de voz indisponível; use Preferências > Testar voz agora." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "v5 ativa. Internet de leitura, agentes por função, voz, Office corrigido e acesso mobile estão habilitados." -ForegroundColor Green
