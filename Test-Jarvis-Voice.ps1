$ErrorActionPreference = "Stop"
$Base = "http://127.0.0.1:4760"
try {
    $diag = Invoke-RestMethod -Uri "$Base/api/voice/diagnostics" -TimeoutSec 4
    Write-Host "Diagnóstico:" -ForegroundColor Cyan
    $diag | ConvertTo-Json -Depth 8 | Write-Host
    $body = @{ text = "Estou ouvindo, senhor. A voz do Jarvis está ativa." } | ConvertTo-Json
    $result = Invoke-RestMethod -Uri "$Base/api/voice/test" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 30
    Write-Host "Voz nativa executada: $($result.backend)" -ForegroundColor Green
} catch {
    Write-Host "Teste pela UI falhou: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "Abra o Jarvis e use Preferências > Testar voz agora." -ForegroundColor Gray
    exit 1
}
