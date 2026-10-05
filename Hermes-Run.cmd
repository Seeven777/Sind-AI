@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
  echo Uso: Hermes-Run.cmd "sua solicitacao"
  exit /b 2
)
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m jarvis hermes-run "%~1"
) else (
  python -m jarvis hermes-run "%~1"
)
endlocal
