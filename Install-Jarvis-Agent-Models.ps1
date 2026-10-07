param(
    [switch]$SkipFast,
    [switch]$SkipCoder
)
$ErrorActionPreference = "Stop"

function Find-Ollama {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($candidate in @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "$env:ProgramFiles\Ollama\ollama.exe"
    )) { if (Test-Path $candidate) { return $candidate } }
    return $null
}

$Ollama = Find-Ollama
if (-not $Ollama) { throw "Ollama não encontrado. Execute Setup-Jarvis-Base.cmd primeiro." }

$models = @()
if (-not $SkipFast) { $models += "llama3.2:1b" }
if (-not $SkipCoder) { $models += "qwen2.5-coder:3b" }

Write-Host "JARVIS - MODELOS LOCAIS POR FUNÇÃO" -ForegroundColor Cyan
Write-Host ""
Write-Host "O modelo principal continua sendo o configurado no Jarvis." -ForegroundColor DarkGray
Write-Host "Estes modelos são complementares e gratuitos/local-first:" -ForegroundColor DarkGray
Write-Host "  llama3.2:1b ........ Inbox / Memory / tarefas rápidas"
Write-Host "  qwen2.5-coder:3b ... Developer / código"
Write-Host ""

$current = & $Ollama list | Out-String
foreach ($model in $models) {
    if ($current -match [regex]::Escape($model)) {
        Write-Host "$model já instalado." -ForegroundColor Green
        continue
    }
    Write-Host "Baixando $model ..." -ForegroundColor Yellow
    & $Ollama pull $model
    if ($LASTEXITCODE -ne 0) { throw "Falha ao baixar $model." }
}

Write-Host ""
Write-Host "Modelos prontos. O Jarvis os detectará automaticamente no próximo início." -ForegroundColor Green
Write-Host "Se algum deles não estiver disponível, o agente usa o modelo principal como fallback." -ForegroundColor DarkGray
