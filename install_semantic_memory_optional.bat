@echo off
cd /d "%~dp0"
echo.
echo Memoria semantica opcional do Jarvis
echo Modelo multilingue local: nomic-embed-text-v2-moe
echo Este download ocupa espaco adicional e usa CPU/RAM apenas quando habilitado.
echo.
where ollama >nul 2>nul
if errorlevel 1 (
  echo Ollama nao encontrado.
  pause
  exit /b 1
)
ollama pull nomic-embed-text-v2-moe
if errorlevel 1 (
  echo Falha ao baixar o modelo.
  pause
  exit /b 1
)
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" enable_semantic_memory.py
) else (
  py enable_semantic_memory.py
)
pause
