param(
    [switch]$SkipStress
)

$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path

function Section($Text) {
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor DarkCyan
    Write-Host " $Text" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkCyan
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Has-Command($Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Find-Python313 {
    if (Has-Command "py") {
        try {
            & py -3.13 -c "import sys; assert sys.version_info[:2] == (3,13)" 2>$null
            if ($LASTEXITCODE -eq 0) {
                return @("py", "-3.13")
            }
        } catch {}
    }

    if (Has-Command "python") {
        try {
            $ver = & python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
            if ($ver.Trim() -eq "3.13") {
                return @("python")
            }
        } catch {}
    }

    return $null
}

Section "JARVIS NEXT - PHASE 0 FOUNDATION"
Write-Host "Projeto: $Project"
Write-Host ""
Write-Host "Esta instalação contém APENAS a fundação."
Write-Host "Não instala Ollama, Node, PySide, modelos, voz ou automação." -ForegroundColor Yellow

# Winget
if (-not (Has-Command "winget")) {
    throw "winget não foi encontrado. Instale/atualize 'App Installer' pela Microsoft Store e execute novamente."
}

Section "1/7 - GIT"
if (-not (Has-Command "git")) {
    Write-Host "Git não encontrado. Instalando Git..."
    & winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao instalar Git pelo winget."
    }
    Refresh-Path
} else {
    Write-Host "Git já está disponível."
}

if (-not (Has-Command "git")) {
    throw "Git foi instalado, mas ainda não está visível no PATH. Feche este PowerShell, abra outro e rode o script novamente."
}
& git --version

Section "2/7 - PYTHON 3.13"
$Py = Find-Python313
if (-not $Py) {
    Write-Host "Python 3.13 não encontrado. Instalando..."
    & winget install --id Python.Python.3.13 -e --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao instalar Python 3.13 pelo winget."
    }
    Refresh-Path
    $Py = Find-Python313
}

if (-not $Py) {
    throw "Python 3.13 foi instalado, mas esta sessão ainda não o encontrou. Reinicie o PowerShell e rode o script novamente."
}

if ($Py.Count -eq 2) {
    & $Py[0] $Py[1] --version
} else {
    & $Py[0] --version
}

Section "3/7 - AMBIENTE VIRTUAL"
Set-Location $Project

if (Test-Path ".venv") {
    Write-Host ".venv já existe. Validando..."
    if (-not (Test-Path ".venv\Scripts\python.exe")) {
        Write-Host "Ambiente incompleto. Recriando..."
        Remove-Item ".venv" -Recurse -Force
    }
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    if ($Py.Count -eq 2) {
        & $Py[0] $Py[1] -m venv .venv
    } else {
        & $Py[0] -m venv .venv
    }
}

$Python = Join-Path $Project ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    throw "Não foi possível criar .venv."
}
& $Python --version

Section "4/7 - INSTALAÇÃO DA FOUNDATION"
& $Python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "Falha ao atualizar pip." }

& $Python -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar Jarvis Next Foundation." }

Section "5/7 - TESTES AUTOMÁTICOS"
& $Python -m pytest
if ($LASTEXITCODE -ne 0) {
    throw "A suíte automática falhou. Não prossiga para a Phase 1."
}

Section "6/7 - SMOKE BOOT"
$Smoke = Join-Path $env:TEMP ("JarvisNext-Smoke-" + [guid]::NewGuid().ToString("N"))
try {
    & $Python -m jarvis --data-dir $Smoke --once
    if ($LASTEXITCODE -ne 0) {
        throw "Smoke boot falhou."
    }
} finally {
    if (Test-Path $Smoke) {
        Remove-Item $Smoke -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Section "7/7 - STRESS"
if ($SkipStress) {
    Write-Host "Stress test ignorado por solicitação (-SkipStress)." -ForegroundColor Yellow
} else {
    & $Python ".\scripts\phase0_stress.py" --boots 50 --tasks 10000 --events 100000
    if ($LASTEXITCODE -ne 0) {
        throw "Stress test falhou. Não prossiga para a Phase 1."
    }
}

Section "PHASE 0 INSTALADA"
Write-Host "Foundation instalada e validada." -ForegroundColor Green
Write-Host ""
Write-Host "Testes:     PASS" -ForegroundColor Green
Write-Host "Smoke boot: PASS" -ForegroundColor Green
if (-not $SkipStress) {
    Write-Host "Stress:     PASS" -ForegroundColor Green
}
Write-Host ""
Write-Host "Nenhum modelo de IA foi instalado."
Write-Host "Nenhum serviço externo foi configurado."
Write-Host ""
Write-Host "Próximo teste manual:"
Write-Host '  .\.venv\Scripts\python.exe -m jarvis --once' -ForegroundColor White
Write-Host ""
Write-Host "Depois envie uma captura desta tela para validarmos a Phase 0 no seu PC."
