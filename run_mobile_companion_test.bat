@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Execute install.bat primeiro.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python mobile_companion_test.py
pause
