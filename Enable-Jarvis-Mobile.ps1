$ErrorActionPreference = "Stop"
$ruleName = "Jarvis Mobile Companion"
$port = 8770
$existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if (-not $existing) {
  New-NetFirewallRule -DisplayName $ruleName -Direction Inbound -Action Allow -Protocol TCP -LocalPort $port -Profile Private | Out-Null
  Write-Host "[OK] Regra criada para redes privadas na porta $port." -ForegroundColor Green
} else {
  Write-Host "[OK] A regra de firewall já existe." -ForegroundColor Green
}
Write-Host "Abra o Jarvis e ative Jarvis Mobile pelo aplicativo ou pelo ícone da bandeja."
