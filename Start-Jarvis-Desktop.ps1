$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$BaseUrl = "http://127.0.0.1:4760/"
$Launcher = Join-Path $Project "Start-Jarvis-UI.ps1"

try { $ping = Invoke-RestMethod -Uri "http://127.0.0.1:4760/api/ping" -Method Get -TimeoutSec 2 } catch { $ping = $null }
if (-not ($ping.ok -eq $true)) {
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Launcher -Page companion | Out-Null
  for ($i=0; $i -lt 120; $i++) {
    Start-Sleep -Milliseconds 250
    try { $ping = Invoke-RestMethod -Uri "http://127.0.0.1:4760/api/ping" -Method Get -TimeoutSec 2; if ($ping.ok -eq $true) { break } } catch {}
  }
}

$custom = $env:JARVIS_DESKTOP_BROWSER
$candidates = @()
if ($custom) { $candidates += $custom }
$candidates += @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "$env:ProgramFiles(x86)\Microsoft\Edge\Application\msedge.exe",
  "$env:LOCALAPPDATA\Programs\Microsoft VS Code\Code.exe"
)
$browser = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $browser) { Start-Process $BaseUrl; exit 0 }

$args = @("--app=$BaseUrl", "--start-maximized", "--disable-features=Translate")
Start-Process -FilePath $browser -ArgumentList $args
