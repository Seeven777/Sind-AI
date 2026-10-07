$ErrorActionPreference = 'SilentlyContinue'
$path = Join-Path $env:LOCALAPPDATA 'JarvisNext\remote\public-access.json'
if (Test-Path $path) {
    $x = Get-Content $path -Raw | ConvertFrom-Json
    Write-Host 'JARVIS ANYWHERE' -ForegroundColor Cyan
    Write-Host "Provider: $($x.provider)"
    Write-Host "Mobile:   $($x.mobile_url)" -ForegroundColor Green
    Write-Host "Desktop:  $($x.desktop_url)" -ForegroundColor Cyan
    Set-Clipboard -Value $x.mobile_url
    Write-Host 'Link mobile copiado.' -ForegroundColor DarkGray
} else {
    Write-Host 'Acesso público ainda não foi configurado.' -ForegroundColor Yellow
    Write-Host 'Execute Enable-Jarvis-Anywhere.cmd.'
}
