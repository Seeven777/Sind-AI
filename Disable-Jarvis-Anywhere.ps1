$ErrorActionPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$path = Join-Path $env:LOCALAPPDATA 'JarvisNext\remote\public-access.json'
if (Test-Path $path) {
    try {
        $x = Get-Content $path -Raw | ConvertFrom-Json
        if ($x.process_id) {
            $p = Get-Process -Id ([int]$x.process_id) -ErrorAction SilentlyContinue
            if ($p) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
        }
    } catch {}
}
Remove-Item $path -Force -ErrorAction SilentlyContinue
Write-Host 'Jarvis Anywhere desativado.' -ForegroundColor Green
