$ErrorActionPreference = 'Stop'
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Port = 4760

function Find-Tailscale {
    $cmd = Get-Command tailscale.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "$env:ProgramFiles\Tailscale\tailscale.exe",
        "$env:LOCALAPPDATA\Tailscale\tailscale.exe"
    )
    foreach ($c in $candidates) { if (Test-Path $c) { return $c } }
    return $null
}

try { $ping = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/ping" -TimeoutSec 2 } catch { $ping = $null }
if (-not ($ping.ok -eq $true)) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project 'Start-Jarvis-UI.ps1') -Page companion | Out-Host
    Start-Sleep -Seconds 1
}

$tailscale = Find-Tailscale
if (-not $tailscale) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Tailscale não está instalado e winget não foi encontrado."
    }
    Write-Host "Instalando Tailscale para acesso mobile HTTPS privado..." -ForegroundColor Cyan
    & winget install -e --id Tailscale.Tailscale --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar Tailscale." }
    Start-Sleep -Seconds 2
    $tailscale = Find-Tailscale
}
if (-not $tailscale) { throw "Tailscale foi instalado, mas tailscale.exe não foi localizado. Reabra este script." }

$status = $null
try { $status = (& $tailscale status --json | ConvertFrom-Json) } catch {}
if (-not $status -or $status.BackendState -ne 'Running') {
    Write-Host "É necessário autenticar este computador no Tailscale. Uma janela poderá ser aberta." -ForegroundColor Yellow
    & $tailscale up
    if ($LASTEXITCODE -ne 0) { throw "Tailscale não foi conectado." }
    Start-Sleep -Seconds 2
}

Write-Host "Ativando HTTPS privado para o Jarvis..." -ForegroundColor Cyan
& $tailscale serve --bg $Port
if ($LASTEXITCODE -ne 0) { throw "Tailscale Serve não foi ativado." }
Start-Sleep -Seconds 1
$status = (& $tailscale status --json | ConvertFrom-Json)
$dns = [string]$status.Self.DNSName
$dns = $dns.TrimEnd('.')
if ([string]::IsNullOrWhiteSpace($dns)) {
    Write-Host "Tailscale Serve foi ativado. Execute 'tailscale serve status' para ver o endereço HTTPS." -ForegroundColor Yellow
    exit 0
}
$url = "https://$dns/mobile"
Set-Clipboard -Value $url
Write-Host ""
Write-Host "JARVIS MOBILE HTTPS" -ForegroundColor Green
Write-Host $url -ForegroundColor Green
Write-Host "Link copiado. Instale Tailscale também no celular usando a mesma conta/tailnet." -ForegroundColor Gray
Write-Host "Com HTTPS, microfone, PWA e recursos de navegador seguro ficam disponíveis." -ForegroundColor Gray
