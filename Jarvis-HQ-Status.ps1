$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Project ".venv\Scripts\python.exe"
$Url = "http://127.0.0.1:4760/api/hq"

try {
    $hq = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 2
    $hq | ConvertTo-Json -Depth 10
    exit 0
} catch {}

if (-not (Test-Path $Python)) { throw ".venv não encontrado." }
& $Python -m jarvis hq
exit $LASTEXITCODE
