param(
  [Parameter(Mandatory=$true)][string]$InstallDir,
  [Parameter(Mandatory=$true)][string]$Repository,
  [ValidateSet("main","stable")][string]$Channel = "main",
  [string]$Branch = "main",
  [int]$CurrentPid = 0,
  [string]$LogPath = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Log([string]$Text) {
  $line = "$(Get-Date -Format s) $Text"
  Write-Host $line
  if ($LogPath) {
    New-Item -ItemType Directory -Path (Split-Path $LogPath -Parent) -Force | Out-Null
    Add-Content -Path $LogPath -Value $line -Encoding UTF8
  }
}
function Copy-Runtime([string]$Source,[string]$Destination) {
  New-Item -ItemType Directory -Path $Destination -Force | Out-Null
  Get-ChildItem $Source -Force | Where-Object { $_.Name -ne ".venv" } | ForEach-Object {
    Copy-Item $_.FullName -Destination $Destination -Recurse -Force
  }
}
function Clear-Runtime([string]$Path) {
  Get-ChildItem $Path -Force -ErrorAction SilentlyContinue | Where-Object { $_.Name -notin @(".venv","launch_jarvis.cmd") } | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
}
function Get-Remote {
  $headers = @{
    "User-Agent" = "SindAI-Jarvis-Updater/1.7"
    "Accept" = "application/vnd.github+json"
    "X-GitHub-Api-Version" = "2022-11-28"
  }
  if ($Channel -eq "stable") {
    $r = Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$Repository/releases/latest"
    return @{
      Zip = $r.zipball_url
      Sha = ""
      Version = ([string]$r.tag_name).TrimStart("v","V")
      Message = [string]$r.name
    }
  }
  $c = Invoke-RestMethod -Headers $headers -Uri "https://api.github.com/repos/$Repository/commits/$Branch"
  return @{
    Zip = "https://github.com/$Repository/archive/refs/heads/$Branch.zip"
    Sha = [string]$c.sha
    Version = ""
    Message = (([string]$c.commit.message) -split "`n")[0]
  }
}

if ($CurrentPid -gt 0) {
  Log "Aguardando o Jarvis encerrar (PID $CurrentPid)..."
  for ($i=0; $i -lt 90; $i++) {
    if (-not (Get-Process -Id $CurrentPid -ErrorAction SilentlyContinue)) { break }
    Start-Sleep -Seconds 1
  }
}

$tempRoot = Join-Path $env:TEMP ("JarvisUpdate_" + [guid]::NewGuid().ToString("N"))
$backupRoot = Join-Path $env:LOCALAPPDATA "SindAI\Backups"
$backupDir = Join-Path $backupRoot (Get-Date -Format "yyyyMMdd_HHmmss")
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
New-Item -ItemType Directory -Path $backupRoot -Force | Out-Null

try {
  Log "Consultando atualização remota..."
  $remote = Get-Remote
  if (-not $remote.Zip) { throw "URL de atualização não encontrada." }

  $zipPath = Join-Path $tempRoot "source.zip"
  Log "Baixando pacote..."
  Invoke-WebRequest -Uri $remote.Zip -OutFile $zipPath -UseBasicParsing

  Log "Validando arquivo ZIP..."
  Expand-Archive -Path $zipPath -DestinationPath $tempRoot -Force
  $source = Get-ChildItem $tempRoot -Directory -Recurse | Where-Object {
    (Test-Path (Join-Path $_.FullName "jarvis_desktop.py")) -and
    (Test-Path (Join-Path $_.FullName "requirements.txt")) -and
    (Test-Path (Join-Path $_.FullName "data\config.json"))
  } | Select-Object -First 1
  if (-not $source) { throw "O pacote remoto não contém uma instalação válida do Jarvis." }

  $remoteConfig = Get-Content (Join-Path $source.FullName "data\config.json") -Raw | ConvertFrom-Json
  $remoteVersion = if ($remote.Version) { $remote.Version } else { [string]$remoteConfig.release_version }

  Log "Criando backup em $backupDir"
  Copy-Runtime $InstallDir $backupDir

  Log "Aplicando arquivos novos..."
  Clear-Runtime $InstallDir
  Copy-Runtime $source.FullName $InstallDir

  Set-Location $InstallDir
  if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "Ambiente virtual local não foi encontrado." }

  Log "Atualizando dependências..."
  & ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if ($LASTEXITCODE -ne 0) { throw "pip install falhou." }

  Log "Validando Python..."
  & ".venv\Scripts\python.exe" -m compileall -q .
  if ($LASTEXITCODE -ne 0) { throw "compileall falhou." }

  $meta = @{
    repository = $Repository
    channel = $Channel
    branch = $Branch
    sha = [string]$remote.Sha
    version = $remoteVersion
    updated_at = (Get-Date).ToUniversalTime().ToString("o")
    message = [string]$remote.Message
  } | ConvertTo-Json -Depth 4
  Set-Content -Path (Join-Path $InstallDir ".jarvis_install.json") -Value $meta -Encoding UTF8

  Log "Atualização concluída para versão $remoteVersion."

  # Retain only the 3 newest backups.
  Get-ChildItem $backupRoot -Directory | Sort-Object LastWriteTime -Descending | Select-Object -Skip 3 | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

  $launcher = Join-Path $InstallDir "launch_jarvis.cmd"
  if (Test-Path $launcher) {
    Log "Reiniciando Jarvis..."
    Start-Process $launcher
  }
}
catch {
  Log "ERRO: $($_.Exception.Message)"
  try {
    Log "Iniciando rollback..."
    Clear-Runtime $InstallDir
    Copy-Runtime $backupDir $InstallDir
    if (Test-Path (Join-Path $InstallDir "requirements.txt")) {
      Log "Restaurando dependências da versão anterior..."
      & ".venv\Scripts\python.exe" -m pip install -r requirements.txt | Out-Null
    }
    Log "Rollback concluído."
    $launcher = Join-Path $InstallDir "launch_jarvis.cmd"
    if (Test-Path $launcher) { Start-Process $launcher }
  } catch {
    Log "FALHA NO ROLLBACK: $($_.Exception.Message)"
  }
}
finally {
  Remove-Item $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}
