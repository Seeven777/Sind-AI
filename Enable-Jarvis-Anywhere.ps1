$ErrorActionPreference = 'Stop'
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Port = 4760
$BaseUrl = "http://127.0.0.1:$Port"
$DataDir = Join-Path $env:LOCALAPPDATA 'JarvisNext'
$RemoteDir = Join-Path $DataDir 'remote'
$RemoteInfoFile = Join-Path $RemoteDir 'public-access.json'
New-Item -ItemType Directory -Path $RemoteDir -Force | Out-Null

function Find-Tailscale {
    $cmd = Get-Command tailscale.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($candidate in @(
        "$env:ProgramFiles\Tailscale\tailscale.exe",
        "$env:LOCALAPPDATA\Tailscale\tailscale.exe"
    )) {
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

function Get-JarvisMobileInfo {
    try { return Invoke-RestMethod -Uri "$BaseUrl/api/mobile" -TimeoutSec 3 }
    catch { return $null }
}

function Ensure-JarvisMobile {
    $info = Get-JarvisMobileInfo
    if ($info -and $info.enabled) { return $info }

    if ($info -and -not $info.enabled) {
        Write-Host 'Reiniciando Jarvis com acesso remoto seguro habilitado...' -ForegroundColor Yellow
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project 'Stop-Jarvis.ps1') | Out-Host
        Start-Sleep -Milliseconds 800
    }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project 'Start-Jarvis-UI.ps1') -Page companion | Out-Host
    for ($i=0; $i -lt 40; $i++) {
        Start-Sleep -Milliseconds 250
        $info = Get-JarvisMobileInfo
        if ($info -and $info.enabled) { return $info }
    }
    throw 'Jarvis não iniciou com o modo remoto habilitado.'
}

$info = Ensure-JarvisMobile
$tailscale = Find-Tailscale
if (-not $tailscale) {
    if (-not (Get-Command winget.exe -ErrorAction SilentlyContinue)) {
        throw 'Tailscale não está instalado e winget não está disponível.'
    }
    Write-Host 'Instalando Tailscale no PC para criar o endereço público do Jarvis...' -ForegroundColor Cyan
    & winget.exe install -e --id Tailscale.Tailscale --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar Tailscale.' }
    Start-Sleep -Seconds 2
    $tailscale = Find-Tailscale
}
if (-not $tailscale) { throw 'tailscale.exe não foi localizado.' }

$status = $null
try { $status = (& $tailscale status --json 2>$null | ConvertFrom-Json) } catch {}
if (-not $status -or $status.BackendState -ne 'Running') {
    Write-Host 'Conectando Tailscale no PC. Na primeira vez poderá abrir uma página de autorização...' -ForegroundColor Yellow
    & $tailscale up
    if ($LASTEXITCODE -ne 0) { throw 'Não foi possível conectar o Tailscale.' }
    Start-Sleep -Seconds 2
}

# Serve e Funnel não podem controlar a mesma porta ao mesmo tempo.
try { & $tailscale serve reset 2>$null | Out-Null } catch {}
try { & $tailscale funnel reset 2>$null | Out-Null } catch {}

Write-Host 'Criando acesso HTTPS público. Nenhum aplicativo será necessário no celular ou no outro computador...' -ForegroundColor Cyan
& $tailscale funnel --bg $Port
if ($LASTEXITCODE -ne 0) {
    throw 'Não foi possível ativar o Tailscale Funnel. Se uma página de autorização foi aberta, aprove o Funnel e execute este arquivo novamente.'
}
Start-Sleep -Seconds 2

$status = (& $tailscale status --json | ConvertFrom-Json)
$dns = [string]$status.Self.DNSName
$dns = $dns.TrimEnd('.')
if ([string]::IsNullOrWhiteSpace($dns)) {
    throw "Funnel foi ativado, mas o nome público do PC não foi encontrado. Execute 'tailscale funnel status'."
}

$token = [string]$info.access_token
if ([string]::IsNullOrWhiteSpace($token)) {
    # Compatibilidade com versões anteriores do endpoint local.
    $token = ([uri]$info.connect_url).Query.TrimStart('?').Split('&') | Where-Object { $_ -like 'token=*' } | ForEach-Object { $_.Substring(6) } | Select-Object -First 1
}
if ([string]::IsNullOrWhiteSpace($token)) { throw 'Token remoto do Jarvis não foi localizado.' }

$root = "https://$dns"
$mobile = "$root/mobile?token=$token"
$desktop = "$root/?token=$token"
$record = [ordered]@{
    enabled = $true
    provider = 'tailscale-funnel'
    public_root = $root
    mobile_url = $mobile
    desktop_url = $desktop
    configured_at = (Get-Date).ToString('o')
}
$record | ConvertTo-Json | Set-Content -Path $RemoteInfoFile -Encoding UTF8
Set-Clipboard -Value $mobile

Write-Host ''
Write-Host 'JARVIS ANYWHERE ATIVO' -ForegroundColor Green
Write-Host ''
Write-Host 'Celular / tablet:' -ForegroundColor Gray
Write-Host $mobile -ForegroundColor Green
Write-Host ''
Write-Host 'Outro computador:' -ForegroundColor Gray
Write-Host $desktop -ForegroundColor Cyan
Write-Host ''
Write-Host 'O link mobile foi copiado para a área de transferência.' -ForegroundColor DarkGray
Write-Host 'O outro dispositivo NÃO precisa instalar Tailscale nem estar no mesmo Wi-Fi.' -ForegroundColor White
Write-Host 'O PC do Jarvis precisa permanecer ligado e conectado à internet.' -ForegroundColor White
Write-Host ''
Write-Host "Endereço salvo em: $RemoteInfoFile" -ForegroundColor DarkGray
Write-Host 'Após o primeiro acesso, o token sai da URL e vira uma sessão protegida no navegador.' -ForegroundColor DarkGray
