@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Enable-Jarvis-Anywhere.ps1"
if errorlevel 1 (
  echo.
  echo Nao foi possivel ativar o acesso remoto do Jarvis.
  pause
  exit /b 1
)
echo.
pause
