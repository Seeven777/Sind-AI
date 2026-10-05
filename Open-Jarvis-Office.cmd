@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Jarvis-UI.ps1" -Page hq
if errorlevel 1 (
  echo.
  echo Nao foi possivel abrir o escritorio 3D do Jarvis.
  pause
)
