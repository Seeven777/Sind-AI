@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Diagnose-Jarvis-Anywhere.ps1"
echo.
pause
