@echo off
setlocal
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "TARGET=%STARTUP%\Jarvis_Autonomous_Operations.cmd"

> "%TARGET%" echo @echo off
>> "%TARGET%" echo cd /d "%~dp0"
>> "%TARGET%" echo start "" "%~dp0run_jarvis.bat"

echo.
echo Jarvis foi adicionado a inicializacao do Windows:
echo %TARGET%
echo.
echo Ele so iniciara automaticamente apos o proximo login.
pause
