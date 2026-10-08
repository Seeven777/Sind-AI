@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Rotate-Jarvis-Remote-Token.ps1"
if errorlevel 1 (
  echo.
  echo Falha ao rotacionar o acesso remoto.
  pause
  exit /b 1
)
echo.
pause
