@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m jarvis ai-status
) else (
  python -m jarvis ai-status
)
endlocal
