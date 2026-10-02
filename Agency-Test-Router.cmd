@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo .venv nao encontrado. Execute Setup-Jarvis-Complete.cmd primeiro.
  exit /b 1
)
".venv\Scripts\python.exe" -m jarvis agency-route "Implemente uma API backend em Python" --limit 5
endlocal
