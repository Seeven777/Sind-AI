@echo off
setlocal
set "TARGET=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Jarvis_Autonomous_Operations.cmd"
if exist "%TARGET%" (
    del "%TARGET%"
    echo Inicializacao automatica removida.
) else (
    echo Nenhum atalho de inicializacao do Jarvis foi encontrado.
)
pause
