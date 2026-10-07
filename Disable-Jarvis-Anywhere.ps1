$ErrorActionPreference = 'Stop'
function Find-Tailscale {
    $cmd = Get-Command tailscale.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($candidate in @("$env:ProgramFiles\Tailscale\tailscale.exe", "$env:LOCALAPPDATA\Tailscale\tailscale.exe")) {
        if (Test-Path $candidate) { return $candidate }
    }
    return $null
}
$tailscale = Find-Tailscale
if ($tailscale) {
    & $tailscale funnel reset | Out-Host
}
$info = Join-Path $env:LOCALAPPDATA 'JarvisNext\remote\public-access.json'
Remove-Item $info -Force -ErrorAction SilentlyContinue
Write-Host 'Acesso público do Jarvis desativado.' -ForegroundColor Green
