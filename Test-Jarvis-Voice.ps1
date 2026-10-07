$ErrorActionPreference = 'Stop'
$Base = 'http://127.0.0.1:4760'
try {
    $diag = Invoke-RestMethod -Uri "$Base/api/voice/diagnostics" -TimeoutSec 5
    Write-Host 'Diagnóstico de voz:' -ForegroundColor Cyan
    $diag | ConvertTo-Json -Depth 8 | Write-Host
    Write-Host "Backend ativo: $($diag.active_backend)" -ForegroundColor Green

    $body = @{ text = 'Estou ouvindo, senhor. Esta é a voz do Jarvis.' } | ConvertTo-Json
    $out = Join-Path $env:TEMP 'jarvis-voice-test.mp3'
    try {
        Invoke-WebRequest -Uri "$Base/api/voice/synthesize" -Method Post -ContentType 'application/json' -Body $body -OutFile $out -TimeoutSec 60 | Out-Null
        if ((Test-Path $out) -and (Get-Item $out).Length -gt 256) {
            Start-Process $out
            Write-Host 'Áudio neural gerado e aberto no player padrão.' -ForegroundColor Green
            exit 0
        }
    } catch {
        Write-Host "Síntese por arquivo falhou: $($_.Exception.Message)" -ForegroundColor Yellow
    }

    $result = Invoke-RestMethod -Uri "$Base/api/voice/test" -Method Post -ContentType 'application/json' -Body $body -TimeoutSec 30
    Write-Host "Fallback nativo executado: $($result.backend)" -ForegroundColor Yellow
} catch {
    Write-Host "Teste falhou: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host 'Abra o Jarvis, confirme que ele está na v6 e execute novamente.' -ForegroundColor Gray
    exit 1
}
