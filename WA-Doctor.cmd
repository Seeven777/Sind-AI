@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m jarvis wa-doctor
) else (
  python -m jarvis wa-doctor
)
endlocal
