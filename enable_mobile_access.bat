@echo off
cd /d "%~dp0"
echo Solicitando permissao de administrador para liberar a porta 8770 apenas em redes privadas...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process powershell -Verb RunAs -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"%CD%\Enable-Jarvis-Mobile.ps1\"'"
pause
