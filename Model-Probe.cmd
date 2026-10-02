@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo .venv nao encontrado. Execute Setup-Jarvis-Base.cmd primeiro.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m jarvis model-probe
echo.
pause
