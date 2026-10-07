@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Enable-Jarvis-Mobile.ps1"
if errorlevel 1 pause
