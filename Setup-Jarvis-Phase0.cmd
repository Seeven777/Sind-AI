@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-Jarvis-Phase0.ps1"
if errorlevel 1 (
  echo.
  echo INSTALACAO INTERROMPIDA. Veja o erro acima.
  pause
  exit /b 1
)
echo.
pause
