$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$DataDir = Join-Path $env:LOCALAPPDATA 'JarvisNext'
$RemoteDir = Join-Path $DataDir 'remote'
$Info = Join-Path $RemoteDir 'public-access.json'
$Err = Join-Path $RemoteDir 'cloudflared.err.log'
$Out = Join-Path $RemoteDir 'cloudflared.log'
Write-Host '=== JARVIS ANYWHERE DIAGNOSTIC ===' -ForegroundColor Cyan
Write-Host ''
try {
    $p = Invoke-RestMethod -Uri 'http://127.0.0.1:4760/api/ping' -TimeoutSec 3
    Write-Host "Local /api/ping: OK ($($p.service))" -ForegroundColor Green
} catch { Write-Host "Local /api/ping: FALHOU - $($_.Exception.Message)" -ForegroundColor Red }
try {
    $ipv4 = Invoke-RestMethod -Uri 'http://127.0.0.1:4760/api/ping' -TimeoutSec 3
    Write-Host "Origem IPv4 cloudflared (127.0.0.1:4760): OK" -ForegroundColor Green
} catch { Write-Host "Origem IPv4 cloudflared: FALHOU - $($_.Exception.Message)" -ForegroundColor Red }
try {
    $m = Invoke-RestMethod -Uri 'http://127.0.0.1:4760/api/mobile' -TimeoutSec 3
    Write-Host "Modo remoto: $($m.enabled)"
} catch { Write-Host 'Modo remoto: não foi possível consultar' -ForegroundColor Red }
try {
    $c = Get-NetTCPConnection -LocalPort 4760 -State Listen -ErrorAction Stop | Select-Object -First 1
    Write-Host "Porta 4760: LISTEN em $($c.LocalAddress)" -ForegroundColor Green
} catch { Write-Host 'Porta 4760: não está escutando' -ForegroundColor Red }
if (Test-Path $Info) {
    $x = Get-Content $Info -Raw | ConvertFrom-Json
    Write-Host "Provider: $($x.provider)"
    Write-Host "Public root: $($x.public_root)"
    if ($x.process_id) {
        $proc = Get-Process -Id ([int]$x.process_id) -ErrorAction SilentlyContinue
        Write-Host "cloudflared PID $($x.process_id): $([bool]$proc)"
    }
    try {
        $r = Invoke-WebRequest -Uri $x.mobile_url -UseBasicParsing -TimeoutSec 12 -MaximumRedirection 5
        Write-Host "Public URL: HTTP $($r.StatusCode)" -ForegroundColor Green
    } catch { Write-Host "Public URL: FALHOU - $($_.Exception.Message)" -ForegroundColor Red }
} else { Write-Host 'Nenhum public-access.json encontrado.' -ForegroundColor Yellow }
Write-Host ''
Write-Host 'Conectividade Cloudflare 7844:' -ForegroundColor Gray
try {
    $tnc = Test-NetConnection region1.v2.argotunnel.com -Port 7844 -WarningAction SilentlyContinue
    Write-Host "TCP 7844: $($tnc.TcpTestSucceeded)" -ForegroundColor $(if($tnc.TcpTestSucceeded){'Green'}else{'Yellow'})
} catch { Write-Host 'TCP 7844: teste indisponível' -ForegroundColor Yellow }
Write-Host ''
if (Test-Path $Err) { Write-Host '--- cloudflared stderr (últimas 25 linhas) ---' -ForegroundColor Gray; Get-Content $Err -Tail 25 }
if (Test-Path $Out) { Write-Host '--- cloudflared stdout (últimas 15 linhas) ---' -ForegroundColor Gray; Get-Content $Out -Tail 15 }
