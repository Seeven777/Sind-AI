@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Repair-Jarvis-Anywhere.ps1"
if errorlevel 1 (
  echo.
  echo Nao foi possivel recriar o Jarvis Anywhere.
  pause
  exit /b 1
)
echo.
pause
