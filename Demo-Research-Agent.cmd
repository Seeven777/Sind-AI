@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -m jarvis demo-agent --prompt "Pesquise como podemos tornar o Jarvis mais confiavel e autonomo sem perder verificacao."
pause
