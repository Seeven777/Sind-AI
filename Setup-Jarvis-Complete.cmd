@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-Jarvis-Complete.ps1"
if errorlevel 1 (
  echo.
  echo INSTALACAO COMPLETA INTERROMPIDA.
  pause
  exit /b 1
)
pause
