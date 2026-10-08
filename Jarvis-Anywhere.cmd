@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Enable-Jarvis-Anywhere.ps1"
if errorlevel 1 (
  echo.
  echo Jarvis Anywhere nao foi ativado. Leia apenas a mensagem acima.
  pause
  exit /b 1
)
echo.
pause
