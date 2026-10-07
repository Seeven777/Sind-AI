param([int]$Port = 4760)
$ErrorActionPreference = "Stop"
$RuleName = "Jarvis Next Mobile"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Solicitando permissão do Windows para liberar somente a rede privada..." -ForegroundColor Cyan
    $args = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`" -Port $Port"
    Start-Process powershell.exe -Verb RunAs -ArgumentList $args -Wait
    exit $LASTEXITCODE
}

$existing = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
if ($existing) {
    $existing | Set-NetFirewallRule -Enabled True -Profile Private -Action Allow | Out-Null
} else {
    New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -Profile Private | Out-Null
}
Write-Host "Acesso mobile liberado na rede PRIVADA para a porta $Port." -ForegroundColor Green
Write-Host "Nenhuma porta foi liberada para redes públicas." -ForegroundColor DarkGray
