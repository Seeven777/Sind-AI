@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Upgrade-Jarvis-v10.ps1"
if errorlevel 1 (
  echo.
  echo JARVIS v10 upgrade failed.
  pause
  exit /b 1
)
echo.
echo JARVIS v10 ready.
pause
