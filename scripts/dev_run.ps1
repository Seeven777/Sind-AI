$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:JARVIS_DATA_DIR = Join-Path $Root ".jarvis-data"
python -m jarvis
