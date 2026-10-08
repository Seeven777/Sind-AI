param(
    [switch]$Auto
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Port = 4760
$BaseUrl = "http://127.0.0.1:$Port"
$DataDir = Join-Path $env:LOCALAPPDATA 'JarvisNext'
$RemoteDir = Join-Path $DataDir 'remote'
$RemoteInfoFile = Join-Path $RemoteDir 'public-access.json'
$NgrokOut = Join-Path $RemoteDir 'ngrok.out.log'
$NgrokErr = Join-Path $RemoteDir 'ngrok.err.log'
New-Item -ItemType Directory -Path $RemoteDir -Force | Out-Null

function Write-Step([string]$Message) {
    if (-not $Auto) { Write-Host $Message -ForegroundColor Cyan }
}

function Test-LocalOrigin {
    try {
        $p = Invoke-RestMethod -Uri "$BaseUrl/api/ping" -TimeoutSec 3
        return ($p.ok -eq $true -and $p.service -eq 'jarvis-ui')
    } catch { return $false }
}

function Get-MobileInfo {
    try { return Invoke-RestMethod -Uri "$BaseUrl/api/mobile" -TimeoutSec 3 }
    catch { return $null }
}

function Ensure-JarvisRemote {
    $info = Get-MobileInfo
    if ($info -and $info.enabled -and (Test-LocalOrigin)) { return $info }

    if (Test-LocalOrigin) {
        Write-Step 'Reiniciando o Jarvis uma vez para habilitar acesso remoto seguro...'
        & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project 'Stop-Jarvis.ps1') | Out-Null
        Start-Sleep -Milliseconds 800
    }

    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project 'Start-Jarvis-UI.ps1') -Page companion | Out-Null
    for ($i=0; $i -lt 120; $i++) {
        Start-Sleep -Milliseconds 250
        $info = Get-MobileInfo
        if ($info -and $info.enabled -and (Test-LocalOrigin)) { return $info }
    }
    throw 'O Jarvis não iniciou em modo remoto seguro.'
}

function Get-AccessToken($Info) {
    $token = [string]$Info.access_token
    if ([string]::IsNullOrWhiteSpace($token) -and $Info.connect_url) {
        try {
            $query = ([uri]$Info.connect_url).Query.TrimStart('?')
            foreach ($part in ($query -split '&')) {
                if ($part -like 'token=*') { $token = $part.Substring(6); break }
            }
        } catch {}
    }
    if ([string]::IsNullOrWhiteSpace($token)) { throw 'Token remoto do Jarvis não foi localizado.' }
    return $token
}

function Stop-OldBridge {
    if (Test-Path $RemoteInfoFile) {
        try {
            $old = Get-Content $RemoteInfoFile -Raw | ConvertFrom-Json
            if ($old.process_id) {
                $proc = Get-Process -Id ([int]$old.process_id) -ErrorAction SilentlyContinue
                if ($proc) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
            }
        } catch {}
    }
    Remove-Item $RemoteInfoFile -Force -ErrorAction SilentlyContinue
}

function Find-Ngrok {
    $cmd = Get-Command ngrok.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($candidate in @(
        "$env:LOCALAPPDATA\Microsoft\WindowsApps\ngrok.exe",
        "$env:ProgramFiles\ngrok\ngrok.exe",
        "$env:ProgramFiles\Ngrok\ngrok.exe"
    )) {
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

function Ensure-Ngrok {
    $exe = Find-Ngrok
    if ($exe) { return $exe }

    if ($Auto) { throw 'ngrok não está instalado. Execute Enable-Jarvis-Anywhere.cmd uma vez manualmente.' }
    Write-Host ''
    Write-Host 'Instalando o ngrok pelo WinGet/Microsoft Store...' -ForegroundColor Cyan
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        Start-Process 'https://ngrok.com/download/windows'
        throw 'WinGet não foi encontrado. A página oficial do ngrok foi aberta; instale-o e execute este arquivo novamente.'
    }
    & $winget.Source install ngrok -s msstore --accept-source-agreements --accept-package-agreements --silent
    Start-Sleep -Seconds 2
    $exe = Find-Ngrok
    if (-not $exe) { throw 'O ngrok não ficou disponível no PATH após a instalação. Feche esta janela e execute novamente.' }
    return $exe
}

function Test-NgrokConfigured([string]$Ngrok) {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'ngrok\ngrok.yml'),
        (Join-Path $env:USERPROFILE '.config\ngrok\ngrok.yml'),
        (Join-Path $env:USERPROFILE '.ngrok2\ngrok.yml')
    )
    foreach ($path in $candidates) {
        if (Test-Path $path) {
            try {
                $text = Get-Content $path -Raw -ErrorAction Stop
                if ($text -match '(?im)^\s*authtoken\s*:') { return $true }
            } catch {}
        }
    }
    return $false
}

function Ensure-NgrokAuth([string]$Ngrok) {
    if (Test-NgrokConfigured $Ngrok) { return }
    if ($Auto) { throw 'ngrok ainda não possui authtoken. Execute Enable-Jarvis-Anywhere.cmd manualmente uma vez.' }

    Write-Host ''
    Write-Host 'PRIMEIRA CONFIGURAÇÃO DO JARVIS ANYWHERE' -ForegroundColor Cyan
    Write-Host '1. Vou abrir a página oficial do ngrok.' -ForegroundColor Gray
    Write-Host '2. Crie/entre na conta gratuita e copie o AUTHTOKEN.' -ForegroundColor Gray
    Write-Host '3. Volte a esta janela e cole o token.' -ForegroundColor Gray
    Start-Process 'https://dashboard.ngrok.com/get-started/your-authtoken'
    $token = Read-Host 'Cole o ngrok authtoken aqui'
    if ([string]::IsNullOrWhiteSpace($token)) { throw 'Authtoken não informado.' }
    & $Ngrok config add-authtoken $token.Trim() | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'O ngrok recusou o authtoken informado.' }
}

function Start-Ngrok([string]$Ngrok, [string]$Token) {
    Remove-Item $NgrokOut,$NgrokErr -Force -ErrorAction SilentlyContinue
    Write-Step 'Abrindo Jarvis Anywhere...'

    $args = @('http',"http://127.0.0.1:$Port",'--log=stdout','--log-format=json')
    $proc = Start-Process -FilePath $Ngrok -ArgumentList $args -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput $NgrokOut -RedirectStandardError $NgrokErr

    $root = $null
    for ($i=0; $i -lt 120; $i++) {
        Start-Sleep -Milliseconds 500
        if ($proc.HasExited) { break }
        try {
            $api = Invoke-RestMethod -Uri 'http://127.0.0.1:4040/api/tunnels' -TimeoutSec 2
            $tunnel = $api.tunnels | Where-Object { $_.public_url -like 'https://*' } | Select-Object -First 1
            if ($tunnel -and $tunnel.public_url) { $root = [string]$tunnel.public_url; break }
        } catch {}
    }

    if (-not $root) {
        $detail = ''
        if (Test-Path $NgrokErr) { $detail += ((Get-Content $NgrokErr -Tail 25 -ErrorAction SilentlyContinue) -join ' ') }
        if (Test-Path $NgrokOut) { $detail += ' ' + ((Get-Content $NgrokOut -Tail 25 -ErrorAction SilentlyContinue) -join ' ') }
        try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        throw "ngrok não criou o endereço público. $detail"
    }

    $escaped = [uri]::EscapeDataString($Token)
    $headers = @{ 'ngrok-skip-browser-warning' = 'true'; 'User-Agent' = 'JarvisAnywhere/8' }
    $verified = $false
    $lastError = ''
    for ($i=0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        try {
            $r = Invoke-WebRequest -Uri "$root/api/ping?token=$escaped" -Headers $headers -UseBasicParsing -TimeoutSec 10
            if ($r.StatusCode -eq 200 -and $r.Content -match 'jarvis-ui') { $verified = $true; break }
        } catch { $lastError = $_.Exception.Message }
    }
    if (-not $verified) {
        try { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue } catch {}
        throw "O endereço público foi criado, mas o teste externo não chegou ao Jarvis. $lastError"
    }

    return [pscustomobject]@{ root=$root; process_id=$proc.Id }
}

$info = Ensure-JarvisRemote
$token = Get-AccessToken $info
$ngrok = Ensure-Ngrok
Ensure-NgrokAuth $ngrok
Stop-OldBridge
$bridge = Start-Ngrok $ngrok $token

$escapedToken = [uri]::EscapeDataString($token)
$mobileUrl = "$($bridge.root)/mobile?token=$escapedToken"
$desktopUrl = "$($bridge.root)/?token=$escapedToken"
$record = [ordered]@{
    provider = 'ngrok'
    public_root = $bridge.root
    mobile_url = $mobileUrl
    desktop_url = $desktopUrl
    process_id = $bridge.process_id
    auto_start = $true
    verified = $true
    created_at = (Get-Date).ToString('o')
}
$record | ConvertTo-Json -Depth 5 | Set-Content -Path $RemoteInfoFile -Encoding UTF8

if (-not $Auto) {
    Write-Host ''
    Write-Host 'JARVIS ANYWHERE ATIVO' -ForegroundColor Green
    Write-Host 'Não é necessário instalar aplicativo no celular ou computador visitante.' -ForegroundColor Gray
    Write-Host ''
    Write-Host 'MOBILE:' -ForegroundColor Cyan
    Write-Host $mobileUrl -ForegroundColor Green
    Write-Host ''
    Write-Host 'DESKTOP:' -ForegroundColor Cyan
    Write-Host $desktopUrl -ForegroundColor Green
    Write-Host ''
    Write-Host 'O link mobile foi copiado.' -ForegroundColor DarkGray
    Write-Host 'No plano gratuito do ngrok, a primeira visita pode exibir uma página de confirmação. Basta escolher Visit Site.' -ForegroundColor DarkGray
    Set-Clipboard -Value $mobileUrl
}
