$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONPATH = Join-Path $root 'src'
$base = 'http://127.0.0.1:4760'

$venvPythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path $venvPythonw) { $python = $venvPythonw }
elif (Test-Path $venvPython) { $python = $venvPython }
else {
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if (-not $cmd) { $cmd = Get-Command python.exe -ErrorAction Stop }
    $python = $cmd.Source
}

function Test-Jarvis {
    try { return ((Invoke-RestMethod -Uri "$base/api/ping" -TimeoutSec 1).ok -eq $true) }
    catch { return $false }
}

if (-not (Test-Jarvis)) {
    Start-Process -FilePath $python -ArgumentList @('-m','jarvis','ui','--no-open','--mobile') -WorkingDirectory $root -WindowStyle Hidden
    for ($i=0; $i -lt 80; $i++) {
        Start-Sleep -Milliseconds 250
        if (Test-Jarvis) { break }
    }
}

if (Test-Jarvis) {
    try {
        $remoteInfoPath = Join-Path $env:LOCALAPPDATA 'JarvisNext\remote\public-access.json'
        if (Test-Path $remoteInfoPath) {
            $remoteInfo = Get-Content $remoteInfoPath -Raw | ConvertFrom-Json
            if ($remoteInfo.auto_start -eq $true) {
                Start-Process powershell.exe -ArgumentList @(
                    '-NoProfile','-WindowStyle','Hidden','-ExecutionPolicy','Bypass','-File',
                    (Join-Path $root 'Enable-Jarvis-Anywhere.ps1'),'-Auto'
                ) -WindowStyle Hidden
            }
        }
    } catch {}
}
