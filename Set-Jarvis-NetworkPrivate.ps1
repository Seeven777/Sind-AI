$ErrorActionPreference = "Stop"

function Write-Info($Text) { Write-Host "[Jarvis] $Text" -ForegroundColor Cyan }
function Write-Ok($Text)   { Write-Host "[OK] $Text" -ForegroundColor Green }
function Write-Warn($Text) { Write-Host "[ATENCAO] $Text" -ForegroundColor Yellow }

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Warn "Este script precisa ser executado como Administrador."
    exit 1
}

Write-Info "Procurando a conexao de rede ativa..."
$profiles = Get-NetConnectionProfile | Where-Object {
    $_.IPv4Connectivity -ne "Disconnected"
}

if (-not $profiles) {
    Write-Warn "Nenhuma conexao IPv4 ativa foi encontrada."
    exit 2
}

foreach ($profile in $profiles) {
    Write-Info ("Interface: {0} | Categoria atual: {1}" -f $profile.Name, $profile.NetworkCategory)
    if ($profile.NetworkCategory -ne "Private") {
        Set-NetConnectionProfile -InterfaceIndex $profile.InterfaceIndex -NetworkCategory Private
        Write-Ok ("Rede '{0}' alterada para Private." -f $profile.Name)
    } else {
        Write-Ok ("Rede '{0}' ja esta como Private." -f $profile.Name)
    }
}

Write-Host ""
Write-Ok "Perfil de rede ajustado. Volte ao Jarvis e clique em Diagnosticar novamente."
Start-Sleep -Seconds 2
