param(
  [string]$Repository = "Seeven777/Sind-AI",
  [string]$Branch = "main",
  [string]$InstallDir = "$env:LOCALAPPDATA\SindAI\Jarvis",
  [switch]$SkipModels,
  [switch]$NoLaunch
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Write-Step($Text) { Write-Host "`n==> $Text" -ForegroundColor Cyan }
function Write-Ok($Text)   { Write-Host "[OK] $Text" -ForegroundColor Green }
function Write-Warn($Text) { Write-Host "[ATENCAO] $Text" -ForegroundColor Yellow }
function Refresh-Path {
  $machine=[Environment]::GetEnvironmentVariable("Path","Machine")
  $user=[Environment]::GetEnvironmentVariable("Path","User")
  $env:Path="$machine;$user"
}
function Has-Command($Name) { return [bool](Get-Command $Name -ErrorAction SilentlyContinue) }

if ($env:OS -ne "Windows_NT") { throw "Este instalador desta release e para Windows 10/11." }

Write-Host "Sind AI - Jarvis Personal GPT 1.4.1" -ForegroundColor Magenta
Write-Host "Instalacao local-first. A Vercel nao executa o modelo nem armazena as conversas."

# Python
if (-not (Has-Command "py")) {
  Write-Step "Python nao encontrado"
  if (Has-Command "winget") {
    Write-Host "Instalando Python 3.12 via WinGet..."
    winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
    Refresh-Path
  } else {
    throw "Python nao encontrado e WinGet indisponivel. Instale Python 3.12+ em https://www.python.org/downloads/windows/ e execute novamente."
  }
}
if (-not (Has-Command "py")) { throw "Python foi instalado, mas o launcher 'py' ainda nao esta no PATH. Feche e reabra o PowerShell e execute novamente." }
Write-Ok "Python encontrado"

# Ollama
if (-not (Has-Command "ollama")) {
  Write-Step "Ollama nao encontrado"
  if (Has-Command "winget") {
    Write-Host "Instalando Ollama via WinGet..."
    winget install --id Ollama.Ollama -e --accept-package-agreements --accept-source-agreements
    Refresh-Path
  } else {
    Write-Warn "WinGet indisponivel. Instale Ollama por https://ollama.com/download/windows e rode o instalador novamente."
    throw "Ollama necessario para o runtime local."
  }
}
Write-Ok "Ollama encontrado"

# Download application code from GitHub
Write-Step "Baixando a versao atual do GitHub"
$tempRoot = Join-Path $env:TEMP ("SindAI_" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
$zipPath = Join-Path $tempRoot "source.zip"
$zipUrl = "https://github.com/$Repository/archive/refs/heads/$Branch.zip"
Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
Expand-Archive -Path $zipPath -DestinationPath $tempRoot -Force
$source = Get-ChildItem $tempRoot -Directory | Where-Object { Test-Path (Join-Path $_.FullName "jarvis_desktop.py") } | Select-Object -First 1
if (-not $source) {
  $source = Get-ChildItem $tempRoot -Directory -Recurse | Where-Object { Test-Path (Join-Path $_.FullName "jarvis_desktop.py") } | Select-Object -First 1
}
if (-not $source) { throw "O pacote baixado nao contem jarvis_desktop.py. Confirme se a branch '$Branch' já recebeu a versão 1.4.1." }


# Resolve the exact commit being installed so the updater can compare future pushes.
$commitSha = ""
try {
  $headers = @{
    "User-Agent" = "SindAI-Jarvis-Installer/1.4.1"
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
  }
  $commitInfo = Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$Repository/commits/$Branch"
  $commitSha = [string]$commitInfo.sha
} catch {
  Write-Warn "Nao foi possivel registrar o SHA remoto agora: $($_.Exception.Message)"
}

Write-Step "Atualizando runtime local"
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
# JarvisData lives in the user home and therefore is not touched here.
Get-ChildItem $InstallDir -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -ne ".venv" } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Copy-Item -Path (Join-Path $source.FullName "*") -Destination $InstallDir -Recurse -Force

Set-Location $InstallDir

Write-Step "Preparando ambiente Python"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
  py -3.12 -m venv .venv
  if ($LASTEXITCODE -ne 0) { py -m venv .venv }
}
& ".venv\Scripts\python.exe" -m pip install --upgrade pip
& ".venv\Scripts\python.exe" -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependencias Python." }
Write-Ok "Dependencias Python instaladas"


# Installation metadata lives with the code, not with personal data.
try {
  $installedConfig = Get-Content (Join-Path $InstallDir "data\config.json") -Raw | ConvertFrom-Json
  $installMeta = @{
    repository = $Repository
    channel = "main"
    branch = $Branch
    sha = $commitSha
    version = [string]$installedConfig.release_version
    installed_at = (Get-Date).ToUniversalTime().ToString("o")
  } | ConvertTo-Json -Depth 4
  Set-Content -Path (Join-Path $InstallDir ".jarvis_install.json") -Value $installMeta -Encoding UTF8
  Write-Ok "Metadados de atualizacao registrados"
} catch {
  Write-Warn "Nao foi possivel gravar os metadados de atualizacao: $($_.Exception.Message)"
}


# Local models chosen by RAM. ModelRouter can still reuse any already installed model.
if (-not $SkipModels) {
  Write-Step "Preparando modelos locais"
  $ramBytes = (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory
  $ramGB = [math]::Round($ramBytes / 1GB, 1)
  Write-Host "RAM detectada: $ramGB GB"
  if ($ramGB -lt 10) {
    $models = @("qwen3:0.6b", "qwen3:1.7b")
  } else {
    $models = @("qwen3:1.7b", "qwen3:4b")
  }
  foreach ($model in $models) {
    Write-Host "Ollama pull $model"
    ollama pull $model
    if ($LASTEXITCODE -ne 0) { Write-Warn "Nao consegui baixar $model agora. O Jarvis pode reutilizar modelos ja instalados." }
  }
}

# Launcher and custom protocol jarvis://
Write-Step "Registrando jarvis:// no Windows"
$launcher = Join-Path $InstallDir "launch_jarvis.cmd"
@"
@echo off
cd /d "$InstallDir"
if not exist ".venv\Scripts\pythonw.exe" exit /b 1
start "" ".venv\Scripts\pythonw.exe" jarvis_desktop.py
"@ | Set-Content -Path $launcher -Encoding ASCII

$protocol = "HKCU:\Software\Classes\jarvis"
New-Item -Path $protocol -Force | Out-Null
Set-ItemProperty -Path $protocol -Name "(default)" -Value "URL:Jarvis Local Protocol"
New-ItemProperty -Path $protocol -Name "URL Protocol" -Value "" -PropertyType String -Force | Out-Null
New-Item -Path "$protocol\shell\open\command" -Force | Out-Null
$commandValue = '"' + $launcher + '" "%1"'
Set-ItemProperty -Path "$protocol\shell\open\command" -Name "(default)" -Value $commandValue
Write-Ok "Protocolo jarvis:// registrado para o usuario atual"

# Start Menu shortcut
try {
  $shortcutPath = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\Sind AI - Jarvis.lnk"
  $shell = New-Object -ComObject WScript.Shell
  $shortcut = $shell.CreateShortcut($shortcutPath)
  $shortcut.TargetPath = $launcher
  $shortcut.WorkingDirectory = $InstallDir
  $shortcut.Description = "Sind AI - Jarvis Personal GPT local"
  $shortcut.Save()
  Write-Ok "Atalho criado no Menu Iniciar"
} catch { Write-Warn "Nao foi possivel criar o atalho do Menu Iniciar: $($_.Exception.Message)" }

Write-Step "Verificacao final"
& ".venv\Scripts\python.exe" doctor.py

Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "`nInstalacao concluida em: $InstallDir" -ForegroundColor Green
Write-Host "Seus dados persistentes permanecem em: $HOME\JarvisData"
Write-Host "O portal da Vercel agora pode abrir este computador usando jarvis://open"

if (-not $NoLaunch) {
  Start-Process $launcher
}
