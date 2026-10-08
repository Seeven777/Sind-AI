@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Disable-Jarvis-Anywhere.ps1"
pause
