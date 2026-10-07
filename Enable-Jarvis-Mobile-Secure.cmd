@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Enable-Jarvis-Mobile-Secure.ps1"
pause
