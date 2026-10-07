param(
    [switch]$SkipModelInference,
    [switch]$SkipComputerUse
)

$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Project ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw ".venv não encontrado. Execute Setup-Jarvis-Complete.cmd primeiro."
}
Set-Location $Project

function Section($Text) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor DarkCyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkCyan
}

$StopScript = Join-Path $Project "Stop-Jarvis.ps1"
if (Test-Path $StopScript) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StopScript
}

Section "1/11 - TESTES AUTOMÁTICOS"
& $Python -m pytest
if ($LASTEXITCODE -ne 0) { throw "pytest falhou." }

Section "2/11 - DOCTOR"
& $Python -m jarvis doctor
if ($LASTEXITCODE -ne 0) { throw "Doctor falhou." }

Section "3/11 - MODELO"
if ($SkipModelInference) {
    Write-Host "Model probe ignorado." -ForegroundColor Yellow
} else {
    & $Python -m jarvis model-probe
    if ($LASTEXITCODE -ne 0) { throw "Model probe falhou." }
}

Section "4/11 - CONNECTORS / WATCHERS"
& $Python -m jarvis sync
if ($LASTEXITCODE -ne 0) { throw "Connector sync falhou." }
& $Python -m jarvis watchers
if ($LASTEXITCODE -ne 0) { throw "Watchers falharam." }

Section "5/11 - AGENTES"
& $Python -m jarvis inbox
if ($LASTEXITCODE -ne 0) { throw "Inbox Agent falhou." }
& $Python -m jarvis curate-memory
if ($LASTEXITCODE -ne 0) { throw "Memory Curator falhou." }

if (-not $SkipModelInference) {
    & $Python -m jarvis demo-agent --prompt "Pesquise de forma curta como validar uma ação de um agente autônomo."
    if ($LASTEXITCODE -ne 0) { throw "Research Agent falhou." }
}

Section "6/11 - AGENCY AGENTS / CODEX"
$agencyStatus = (& $Python -m jarvis agency-status | Out-String)
if ($LASTEXITCODE -ne 0) { throw "Agency status falhou." }
Write-Host $agencyStatus
if ($agencyStatus -match '"agents"\s*:\s*([1-9][0-9]*)') {
    $agencyCount = [int]$Matches[1]
    Write-Host "Agency Agents detectados: $agencyCount" -ForegroundColor Green
    $agencyRoute = (& $Python -m jarvis agency-route "Implemente uma API backend em Python" --limit 3 | Out-String)
    if ($LASTEXITCODE -ne 0) { throw "AgentRouter Agency falhou." }
    Write-Host $agencyRoute
    if ($agencyRoute -notmatch 'agency\.') { throw "AgentRouter não selecionou especialista Agency." }
} else {
    Write-Host "Agency Agents não detectado; integração opcional permanece degradada com segurança." -ForegroundColor Yellow
}

Section "7/11 - BRIEFING / CAPABILITIES / AI MESH"
& $Python -m jarvis briefing
if ($LASTEXITCODE -ne 0) { throw "Briefing falhou." }
& $Python -m jarvis inventory
if ($LASTEXITCODE -ne 0) { throw "Inventário falhou." }
& $Python -m jarvis ai-status
if ($LASTEXITCODE -ne 0) { throw "AI Mesh status falhou." }

Section "8/11 - COMPUTER USE"
if ($SkipComputerUse) {
    Write-Host "Computer Use ignorado." -ForegroundColor Yellow
} else {
    $browser = (& $Python -m jarvis browser-doctor | Out-String)
    if ($browser -notmatch '"status": "healthy"') {
        throw "Playwright não está saudável. Execute Setup-Jarvis-Extras.cmd."
    }

    $windows = (& $Python -m jarvis windows-doctor | Out-String)
    if ($windows -notmatch '"status": "healthy"') {
        throw "Windows UIA não está saudável. Execute Setup-Jarvis-Extras.cmd."
    }
    Write-Host "Browser e Windows UIA: PASS" -ForegroundColor Green
}

Section "9/11 - UI LOCAL"
$proc = Start-Process -FilePath $Python -ArgumentList @("-m","jarvis","ui","--no-open","--mobile") -WorkingDirectory $Project -PassThru
$ready = $false
for ($i=0; $i -lt 120; $i++) {
    Start-Sleep -Milliseconds 250
    try {
        $ping = Invoke-RestMethod -Uri "http://127.0.0.1:4760/api/ping" -TimeoutSec 1
        if ($ping.ok -eq $true) { $ready = $true; break }
    } catch {}
    if ($proc.HasExited) { break }
}
if (-not $ready) { throw "UI local não iniciou." }

$routes = @("/", "/hq", "/mission-control", "/agents", "/projects", "/memory", "/system")
foreach ($route in $routes) {
    $response = Invoke-WebRequest -UseBasicParsing -Uri ("http://127.0.0.1:4760" + $route) -TimeoutSec 5
    if ($response.StatusCode -ne 200) { throw "Falha na rota UI: $route" }
    Write-Host "$route PASS" -ForegroundColor Green
}

Section "10/11 - APIS"
$apis = @("/api/hq","/api/briefing","/api/system","/api/ai-mesh","/api/projects","/api/agents","/api/agency","/api/memory","/api/capabilities","/api/mobile","/api/voice/diagnostics")
foreach ($route in $apis) {
    $response = Invoke-WebRequest -UseBasicParsing -Uri ("http://127.0.0.1:4760" + $route) -TimeoutSec 5
    if ($response.StatusCode -ne 200) { throw "Falha na API: $route" }
    Write-Host "$route PASS" -ForegroundColor Green
}
$mobile = Invoke-RestMethod -Uri "http://127.0.0.1:4760/api/mobile" -TimeoutSec 5
if (-not $mobile.enabled -or -not $mobile.connect_url) { throw "Acesso mobile protegido não foi ativado." }
Write-Host "Mobile protegido: PASS" -ForegroundColor Green

Section "11/11 - ENCERRAMENTO LIMPO"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $StopScript
Start-Sleep -Milliseconds 500

Write-Host ""
Write-Host "JARVIS NEXT PRESENCE v5 VALIDADO." -ForegroundColor Green
Write-Host "Recursos externos sem configuração (Google, voz, MCP, A2A) podem aparecer como unconfigured/empty sem falhar o Core."
