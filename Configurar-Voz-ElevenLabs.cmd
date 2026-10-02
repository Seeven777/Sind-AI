@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" "scripts\configure_elevenlabs_voice.py"
) else (
  python "scripts\configure_elevenlabs_voice.py"
)
echo.
pause
