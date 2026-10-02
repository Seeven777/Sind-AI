@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-Jarvis-Extras.ps1"
if errorlevel 1 (
  echo.
  echo INSTALACAO DOS EXTRAS FALHOU.
  pause
  exit /b 1
)
pause
