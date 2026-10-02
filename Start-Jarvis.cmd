@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Jarvis-UI.ps1" -Page companion
if errorlevel 1 (
  echo.
  echo Nao foi possivel iniciar o Jarvis.
  pause
)
