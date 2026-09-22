$ruleName = "Jarvis Mobile Companion"
Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
Write-Host "[OK] Regra do Jarvis Mobile removida." -ForegroundColor Green
