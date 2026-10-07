$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseUrl = "http://127.0.0.1:4760"

function Get-MobileInfo {
    try { return Invoke-RestMethod -Uri "$BaseUrl/api/mobile" -Method Get -TimeoutSec 3 }
    catch { return $null }
}

$info = Get-MobileInfo
if (-not $info) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Project "Start-Jarvis-UI.ps1") -Page companion
    Start-Sleep -Seconds 1
    $info = Get-MobileInfo
}
if (-not $info) { throw "Não consegui iniciar ou localizar o Jarvis." }
if (-not $info.enabled) {
    throw "O Jarvis em execução foi iniciado sem modo mobile. Feche o Jarvis e execute Start-Jarvis-Mobile.cmd novamente."
}

Write-Host "" 
Write-Host "JARVIS MOBILE" -ForegroundColor Cyan
Write-Host "Conecte o celular à mesma rede Wi-Fi deste computador." -ForegroundColor Gray
Write-Host "Abra este endereço no celular:" -ForegroundColor Gray
Write-Host $info.connect_url -ForegroundColor Green
Set-Clipboard -Value $info.connect_url
Write-Host "" 
Write-Host "O link também foi copiado para a área de transferência." -ForegroundColor DarkGray
Write-Host "Na primeira utilização, se o Windows solicitar acesso à rede, permita apenas Redes Privadas." -ForegroundColor DarkGray
