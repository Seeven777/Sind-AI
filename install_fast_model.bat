@echo off
echo.
echo =========================================
echo  JARVIS FAST CONVERSATION MODEL
echo =========================================
echo.
where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama CLI nao foi encontrado.
  pause
  exit /b 1
)
echo Instalando qwen3:1.7b...
ollama pull qwen3:1.7b
echo.
ollama list
pause
