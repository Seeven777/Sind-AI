@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m jarvis nemotron-probe
) else (
  python -m jarvis nemotron-probe
)
set ERR=%ERRORLEVEL%
endlocal & exit /b %ERR%
