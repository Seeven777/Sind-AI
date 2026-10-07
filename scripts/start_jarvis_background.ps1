$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONPATH = Join-Path $root 'src'

$venvPythonw = Join-Path $root '.venv\Scripts\pythonw.exe'
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (Test-Path $venvPythonw) { $python = $venvPythonw }
elif (Test-Path $venvPython) { $python = $venvPython }
else {
    $cmd = Get-Command pythonw.exe -ErrorAction SilentlyContinue
    if (-not $cmd) { $cmd = Get-Command python.exe -ErrorAction Stop }
    $python = $cmd.Source
}

& $python -m jarvis ui --no-open --mobile
