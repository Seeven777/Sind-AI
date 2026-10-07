param(
    [switch]$SkipVoiceInstall,
    [switch]$SkipModelDownload,
    [switch]$SkipMobileFirewall
)
$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Project ".venv\Scripts\python.exe"

Write-Host "JARVIS PRESENCE v6 - VOZ + MOBILE" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $Python)) {
    throw ".venv não encontrado. Execute Setup-Jarvis-Base.cmd primeiro."
}

$stop = Join-Path $Project "Stop-Jarvis.ps1"
if (Test-Path $stop) {
    Write-Host "Encerrando instância anterior..." -ForegroundColor DarkGray
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $stop | Out-Host
}

if (-not $SkipVoiceInstall) {
    Write-Host ""
    Write-Host "Instalando voz neural gratuita (Edge TTS)..." -ForegroundColor Cyan
    & $Python -m pip install --upgrade "edge-tts>=7.2.8,<8"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Edge TTS não foi instalado. Jarvis continuará com Piper/Windows como fallback." -ForegroundColor Yellow
    } else {
        [Environment]::SetEnvironmentVariable('JARVIS_TTS_PROVIDER','edge-tts','User')
        [Environment]::SetEnvironmentVariable('JARVIS_EDGE_VOICE','pt-BR-AntonioNeural','User')
        [Environment]::SetEnvironmentVariable('JARVIS_EDGE_RATE','-6%','User')
        [Environment]::SetEnvironmentVariable('JARVIS_EDGE_PITCH','-14Hz','User')
        $env:JARVIS_TTS_PROVIDER='edge-tts'
        $env:JARVIS_EDGE_VOICE='pt-BR-AntonioNeural'
        $env:JARVIS_EDGE_RATE='-6%'
        $env:JARVIS_EDGE_PITCH='-14Hz'
        Write-Host "Voz Jarvis: pt-BR-AntonioNeural · perfil calmo/sintético." -ForegroundColor Green
    }
}

if (-not $SkipModelDownload) {
    $models = Join-Path $Project "Install-Jarvis-Agent-Models.ps1"
    if (Test-Path $models) {
        try { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $models | Out-Host }
        catch { Write-Host "Modelos auxiliares não foram atualizados: $($_.Exception.Message)" -ForegroundColor Yellow }
    }
}

if (-not $SkipMobileFirewall) {
    $mobile = Join-Path $Project "Enable-Jarvis-Mobile.ps1"
    if (Test-Path $mobile) {
        Write-Host ""
        Write-Host "Preparando Jarvis Mobile na rede privada..." -ForegroundColor Cyan
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $mobile | Out-Host
    }
}

Write-Host ""
Write-Host "Validando arquivos críticos..." -ForegroundColor Cyan
& $Python -m pytest tests/product/test_presence_v6.py tests/product/test_presence_v5.py tests/product/test_presence_v4.py tests/product/test_companion_presence_v2.py
if ($LASTEXITCODE -ne 0) { throw "Validação da v6 falhou." }

Write-Host ""
Write-Host "Iniciando Jarvis v6..." -ForegroundColor Cyan
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project "Start-Jarvis-UI.ps1") -Page companion | Out-Host
Start-Sleep -Seconds 1

try {
    $diag = Invoke-RestMethod -Uri "http://127.0.0.1:4760/api/voice/diagnostics" -TimeoutSec 5
    Write-Host "Voz ativa: $($diag.active_backend)" -ForegroundColor Green
    if ($diag.active_backend -eq 'windows-sapi') {
        Write-Host "Edge TTS não ficou ativo; execute Test-Jarvis-Voice.cmd e envie o diagnóstico se a voz continuar incorreta." -ForegroundColor Yellow
    }
} catch {
    Write-Host "Não consegui ler o diagnóstico de voz." -ForegroundColor Yellow
}

try {
    $mobileInfo = Invoke-RestMethod -Uri "http://127.0.0.1:4760/api/mobile" -TimeoutSec 5
    if ($mobileInfo.enabled -and $mobileInfo.connect_url) {
        Set-Clipboard -Value $mobileInfo.connect_url
        Write-Host ""
        Write-Host "Jarvis Mobile pronto:" -ForegroundColor Cyan
        Write-Host $mobileInfo.connect_url -ForegroundColor Green
        Write-Host "O link foi copiado. Abra no celular conectado à mesma rede Wi-Fi." -ForegroundColor DarkGray
    }
} catch {
    Write-Host "Link mobile local ainda indisponível." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "v6 ativa." -ForegroundColor Green
Write-Host "Para voz/microfone mobile com HTTPS e uso fora da LAN, execute Enable-Jarvis-Mobile-Secure.cmd." -ForegroundColor Gray
