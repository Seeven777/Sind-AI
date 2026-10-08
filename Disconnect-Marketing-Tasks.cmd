@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -m jarvis marketing-disconnect
pause
