@echo off
setlocal
if not exist ".venv\Scripts\python.exe" (
  echo ERRO: execute este arquivo na raiz do projeto JARVIS, com .venv existente.
  exit /b 2
)
".venv\Scripts\python.exe" apply_computer_runtime_v2.py
exit /b %errorlevel%
