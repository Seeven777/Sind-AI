$ErrorActionPreference='Stop'
$cmd=Get-Command tailscale.exe -ErrorAction SilentlyContinue
if(-not $cmd){$candidate="$env:ProgramFiles\Tailscale\tailscale.exe";if(Test-Path $candidate){$cmd=Get-Item $candidate}}
if(-not $cmd){throw 'Tailscale não encontrado.'}
& $cmd.Source serve off
Write-Host 'Tailscale Serve do Jarvis desativado.' -ForegroundColor Green
