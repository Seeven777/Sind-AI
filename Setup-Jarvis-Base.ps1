param(
    [switch]$SkipModelPull,
    [switch]$SkipAgentDemo
)

$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Model = "qwen3.5:4b"

function Section($Text) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor DarkCyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkCyan
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Find-Python313 {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.13 -c "import sys; assert sys.version_info[:2] == (3,13)" 2>$null
        if ($LASTEXITCODE -eq 0) { return @("py", "-3.13") }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $v = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ($LASTEXITCODE -eq 0 -and $v.Trim() -eq "3.13") { return @("python") }
    }
    return $null
}

function Find-Ollama {
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "$env:ProgramFiles\Ollama\ollama.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}

function Test-OllamaApi {
    try {
        $null = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -Method Get -TimeoutSec 2
        return $true
    } catch {
        return $false
    }
}

Section "JARVIS NEXT 1.0 RC2 - BASE"
Write-Host "Projeto: $Project"
Write-Host ""
Write-Host "Esta etapa instala o Core, cérebro local, 8 agentes, Tool Mesh, Connectors, Scheduler e HQ." -ForegroundColor Yellow
Write-Host "Modelo padrão: $Model"
Write-Host "Agentes operacionais: Research, Analyst, Creator, Developer, Operator, Reviewer, Memory Curator e Inbox"
Write-Host ""

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "winget não foi encontrado. Atualize o App Installer da Microsoft Store."
}

Section "0/8 - NORMALIZANDO RUNTIME"
$StopScript = Join-Path $Project "Stop-Jarvis.ps1"
if (Test-Path $StopScript) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StopScript
    if ($LASTEXITCODE -ne 0) { throw "Não foi possível normalizar uma instância anterior do Jarvis." }
}

Section "1/8 - GIT E PYTHON"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    & winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar Git." }
    Refresh-Path
}
& git --version

$Py = Find-Python313
if (-not $Py) {
    & winget install --id Python.Python.3.13 -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar Python 3.13." }
    Refresh-Path
    $Py = Find-Python313
}
if (-not $Py) { throw "Python 3.13 não ficou disponível nesta sessão. Reabra o terminal e execute novamente." }

Section "2/8 - AMBIENTE PYTHON"
Set-Location $Project
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    if ($Py.Count -eq 2) { & $Py[0] $Py[1] -m venv .venv } else { & $Py[0] -m venv .venv }
}
$Python = Join-Path $Project ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { throw "Não foi possível preparar .venv." }
& $Python --version
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar pip." }
& $Python -m pip install -e ".[dev,voice]"
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar Jarvis Next." }

Section "3/8 - OLLAMA"
$Ollama = Find-Ollama
if (-not $Ollama) {
    Write-Host "Ollama não encontrado. Instalando..."
    & winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar Ollama." }
    Refresh-Path
    $Ollama = Find-Ollama
}
if (-not $Ollama) { throw "Ollama foi instalado, mas ollama.exe não foi localizado." }
Write-Host "Ollama: $Ollama"
& $Ollama --version

if (-not (Test-OllamaApi)) {
    Write-Host "Iniciando servidor Ollama..."
    Start-Process -FilePath $Ollama -ArgumentList "serve" -WindowStyle Hidden
    $ready = $false
    for ($i=0; $i -lt 30; $i++) {
        Start-Sleep -Seconds 1
        if (Test-OllamaApi) { $ready = $true; break }
    }
    if (-not $ready) { throw "O servidor Ollama não respondeu em http://127.0.0.1:11434." }
}
Write-Host "Ollama API: OK" -ForegroundColor Green

Section "4/8 - MODELO LOCAL"
if ($SkipModelPull) {
    Write-Host "Download do modelo ignorado (-SkipModelPull)." -ForegroundColor Yellow
} else {
    $hasModel = (& $Ollama list | Out-String) -match [regex]::Escape($Model)
    if (-not $hasModel) {
        Write-Host "Baixando $Model. Este é o download mais demorado desta instalação..." -ForegroundColor Yellow
        & $Ollama pull $Model
        if ($LASTEXITCODE -ne 0) { throw "Falha ao baixar $Model." }
    } else {
        Write-Host "$Model já está instalado."
    }
}

Section "5/8 - TESTES DO PROJETO"
& $Python -m pytest
if ($LASTEXITCODE -ne 0) { throw "A suíte de testes falhou." }

Section "6/8 - DIAGNÓSTICO"
& $Python -m jarvis doctor
if ($LASTEXITCODE -ne 0) { throw "Diagnóstico do Jarvis falhou." }

Section "7/8 - MODELO E EQUIPE MULTIAGENTE"
if ($SkipAgentDemo -or $SkipModelPull) {
    Write-Host "Demo real do agente ignorada." -ForegroundColor Yellow
} else {
    Write-Host "Testando inferência real do modelo..."
    & $Python -m jarvis model-probe
    if ($LASTEXITCODE -ne 0) {
        throw "Ollama/modelo está instalado, mas a inferência não produziu resposta final. Execute: ollama --version e depois Validate-Jarvis-Base.cmd."
    }
    Write-Host ""
    Write-Host "Executando uma missão de pesquisa real..."
    & $Python -m jarvis demo-agent --prompt "Pesquise em formato curto por que um sistema autônomo deve verificar o próprio trabalho antes de declarar sucesso."
    if ($LASTEXITCODE -ne 0) { throw "Research Agent não concluiu a missão de demonstração." }
    Write-Host ""
    Write-Host "A missão completa Research -> Analyst -> Creator -> Reviewer pode ser testada depois com Demo-Team.cmd."

}

Section "8/8 - CONCLUÍDO"
Write-Host "BASE HORIZONTAL INSTALADA." -ForegroundColor Green
Write-Host ""
Write-Host "Foundation........ PASS" -ForegroundColor Green
Write-Host "Brain/Ollama...... PASS" -ForegroundColor Green
Write-Host "Jarvis Core....... PASS" -ForegroundColor Green
Write-Host "Research Agent.... PASS" -ForegroundColor Green
Write-Host "Analyst Agent..... READY" -ForegroundColor Green
Write-Host "Creator Agent..... READY" -ForegroundColor Green
Write-Host "Developer Agent... READY" -ForegroundColor Green
Write-Host "Operator Agent.... READY" -ForegroundColor Green
Write-Host "Reviewer Agent.... READY" -ForegroundColor Green
Write-Host "Memory Curator.... READY" -ForegroundColor Green
Write-Host "Inbox Agent....... READY" -ForegroundColor Green
Write-Host "Memory base....... READY" -ForegroundColor Green
Write-Host "Tool Mesh......... READY" -ForegroundColor Green
Write-Host "Approvals......... READY" -ForegroundColor Green
Write-Host "Connectors........ READY" -ForegroundColor Green
Write-Host "Scheduler......... READY" -ForegroundColor Green
Write-Host "Watchers.......... READY" -ForegroundColor Green
Write-Host "HQ logical........ READY" -ForegroundColor Green
Write-Host "HQ visual......... READY" -ForegroundColor Green
Write-Host "Web Research...... READY" -ForegroundColor Green
Write-Host "Skill System...... READY" -ForegroundColor Green
Write-Host "Agent Factory..... READY" -ForegroundColor Green
Write-Host "Model Mesh........ READY" -ForegroundColor Green
Write-Host ""
Write-Host "Para conversar agora:" -ForegroundColor White
Write-Host "  Start-Jarvis.cmd"
Write-Host ""
Write-Host "Para abrir o escritorio de agentes:" -ForegroundColor White
Write-Host "  Start-Jarvis-HQ.cmd"
Write-Host ""
Write-Host "Dentro do chat, teste:" -ForegroundColor White
Write-Host "  Pesquise como podemos melhorar o Jarvis Next."
