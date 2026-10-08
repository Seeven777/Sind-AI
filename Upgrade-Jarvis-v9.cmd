@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Upgrade-Jarvis-v9.ps1"
if errorlevel 1 (
  echo.
  echo JARVIS v9 upgrade failed.
  pause
  exit /b 1
)
echo.
echo JARVIS v9 ready.
pause
