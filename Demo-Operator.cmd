@echo off
setlocal
cd /d "%~dp0"
".venv\Scripts\python.exe" -m jarvis operator time
echo.
echo Teste de leitura: .venv\Scripts\python.exe -m jarvis operator list --path "C:\"
echo Teste de escrita com aprovacao:
echo .venv\Scripts\python.exe -m jarvis operator write --path "teste.txt" --content "arquivo criado pelo Operator"
pause
