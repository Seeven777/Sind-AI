@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Upgrade-Jarvis-v6.ps1"
if errorlevel 1 pause
