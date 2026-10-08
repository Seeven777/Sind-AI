@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Upgrade-Jarvis-v11.1.ps1"
if errorlevel 1 (
  echo.
  echo JARVIS v11.1 upgrade failed.
  pause
  exit /b 1
)
echo.
echo JARVIS v11.1 ready.
pause
