@echo off
setlocal
cd /d "%~dp0"
set PY=python
if exist ".venv\Scripts\python.exe" set PY=.venv\Scripts\python.exe

echo ===== AUDITORIA DE LIMPEZA =====
%PY% scripts\cleanup_project.py
echo.
echo Nenhum arquivo foi removido.
echo Para limpar caches seguros, execute:
echo   %PY% scripts\cleanup_project.py --apply
pause
