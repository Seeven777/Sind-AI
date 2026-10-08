$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$path = Join-Path $env:LOCALAPPDATA 'JarvisNext\remote\public-access.json'
if (-not (Test-Path $path)) {
    Write-Host 'Jarvis Anywhere ainda não foi ativado.' -ForegroundColor Yellow
    Write-Host 'Execute Enable-Jarvis-Anywhere.cmd.'
    exit 1
}
$x = Get-Content $path -Raw | ConvertFrom-Json
$procAlive = $false
if ($x.process_id) { $procAlive = [bool](Get-Process -Id ([int]$x.process_id) -ErrorAction SilentlyContinue) }
$localOk = $false
try {
    $p = Invoke-RestMethod -Uri 'http://127.0.0.1:4760/api/ping' -TimeoutSec 3
    $localOk = ($p.ok -eq $true -and $p.service -eq 'jarvis-ui')
} catch {}
$publicOk = $false
try {
    $headers = @{ 'ngrok-skip-browser-warning'='true'; 'User-Agent'='JarvisAnywhereStatus/8' }
    $r = Invoke-WebRequest -Uri $x.mobile_url -Headers $headers -UseBasicParsing -TimeoutSec 12 -MaximumRedirection 5
    $publicOk = ($r.StatusCode -eq 200)
} catch {}
Write-Host 'JARVIS ANYWHERE' -ForegroundColor Cyan
Write-Host "Provider:       $($x.provider)"
Write-Host "Jarvis local:   $localOk" -ForegroundColor $(if($localOk){'Green'}else{'Red'})
Write-Host "Ponte ativa:    $procAlive" -ForegroundColor $(if($procAlive){'Green'}else{'Red'})
Write-Host "Acesso público: $publicOk" -ForegroundColor $(if($publicOk){'Green'}else{'Red'})
Write-Host "Mobile:  $($x.mobile_url)" -ForegroundColor Green
Write-Host "Desktop: $($x.desktop_url)" -ForegroundColor Cyan
if ($localOk -and $procAlive -and $publicOk) {
    Set-Clipboard -Value $x.mobile_url
    Write-Host 'Link mobile copiado.' -ForegroundColor DarkGray
    exit 0
}
Write-Host ''
Write-Host 'Execute Repair-Jarvis-Anywhere.cmd.' -ForegroundColor Yellow
exit 2
