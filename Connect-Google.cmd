@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -m jarvis google-auth
if errorlevel 1 (
  echo.
  echo Nao foi possivel autorizar Google.
)
pause
