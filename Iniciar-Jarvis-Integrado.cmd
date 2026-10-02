@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" "run_integrated_jarvis.py"
if errorlevel 1 pause
