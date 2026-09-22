@echo off
cd /d "%~dp0"

echo.
echo ===============================================
echo  JARVIS COGNITIVE FOUNDATION 1.0a
echo ===============================================
echo.
echo GPT pessoal local - nucleo sem API paga obrigatoria.
echo Hardware de referencia: Ryzen 5 5600GT / 16 GB / qwen3:4b CPU.
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo Python launcher "py" nao foi encontrado.
    pause
    exit /b 1
)

if not exist ".venv" (
    py -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt

echo.
echo Instalacao concluida.
echo.
echo Testes recomendados:
echo   1. run_cognitive_test.bat
echo   2. run_self_test.bat
echo   3. run_foundation_test.bat
echo   4. run_routing_test.bat
echo   5. run_health_test.bat
echo   6. run_browser_test.bat
echo   7. run_jarvis.bat
echo.
echo Teste online opcional de fontes publicas:
echo   run_public_data_online_test.bat
echo.
echo Memoria semantica opcional - NAO e necessaria:
echo   install_semantic_memory_optional.bat
echo.
pause


echo.
echo Para conversa natural rapida, execute UMA VEZ:
echo   install_fast_model.bat
echo O qwen3:1.7b fica para conversa; qwen3:4b para raciocinio/ferramentas.
echo.
