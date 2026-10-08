@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Upgrade-Jarvis-v12.ps1"
if errorlevel 1 (
  echo.
  echo Falha ao atualizar Jarvis v12.
  pause
)
