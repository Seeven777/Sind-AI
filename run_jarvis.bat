@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo Execute install.bat primeiro.
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" app.py
