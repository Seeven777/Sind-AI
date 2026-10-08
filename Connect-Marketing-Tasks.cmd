@echo off
setlocal
cd /d "%~dp0"
echo.
echo JARVIS - conectar organizador de tarefas
".venv\Scripts\python.exe" -m jarvis marketing-auth
if errorlevel 1 (
  echo.
  echo Nao foi possivel concluir a conexao com o organizador.
  echo Se o navegador nao abriu, execute Setup-Jarvis-Extras.cmd e tente novamente.
)
pause
