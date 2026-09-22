@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute install.bat primeiro.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" self_test.py
pause
