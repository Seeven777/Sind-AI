@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -m jarvis demo-team --prompt "Monte uma equipe e desenvolva um plano concreto para evoluir o Jarvis Next sem perder confiabilidade."
pause
