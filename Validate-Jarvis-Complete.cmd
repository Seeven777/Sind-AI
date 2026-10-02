@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Validate-Jarvis-Complete.ps1"
if errorlevel 1 (
  echo.
  echo VALIDACAO COMPLETA FALHOU.
  pause
  exit /b 1
)
pause
