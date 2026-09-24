@echo off
setlocal
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe apply_phase4_whatsapp_interactive_fix.py
) else (
  python apply_phase4_whatsapp_interactive_fix.py
)
if errorlevel 1 pause
