@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Jarvis-Desktop.ps1"
if errorlevel 1 (
  echo.
  echo Nao foi possivel iniciar o Jarvis Desktop.
  pause
)
