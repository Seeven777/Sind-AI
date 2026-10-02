$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Data = Join-Path $Root ".jarvis-data"
if (Test-Path $Data) {
    Remove-Item $Data -Recurse -Force
}
Write-Host "Test data removed: $Data"
