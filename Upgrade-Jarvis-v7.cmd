@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Upgrade-Jarvis-v7.ps1"
if errorlevel 1 (
  echo.
  echo Falha ao atualizar/iniciar Jarvis v7.
  pause
  exit /b 1
)
echo.
pause
