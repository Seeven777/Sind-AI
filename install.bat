@echo off
cd /d "%~dp0"

echo.
echo ===============================================
echo  JARVIS PERSONAL GPT 1.0 RC
echo ===============================================
echo.
echo GPT pessoal local - sem API paga obrigatoria.
echo Arquitetura adaptativa: conversa, memoria, pesquisa,
echo ferramentas, projetos, anexos, automacoes e integracoes.
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
echo Instalacao Python concluida.
echo.
echo Se qwen3:1.7b ainda nao estiver instalado:
echo   install_fast_model.bat
echo.
echo O Jarvis tambem consegue reutilizar outros modelos
echo conversacionais ja instalados no Ollama.
echo.
echo TESTE RAPIDO:
echo   1. run_doctor.bat
echo   2. run_personal_gpt_test.bat
echo   3. run_cognitive_test.bat
echo   4. run_self_test.bat
echo   5. run_foundation_test.bat
echo   6. run_model_router_test.bat
echo   7. run_routing_test.bat
echo   8. run_health_test.bat
echo   9. run_browser_test.bat
echo  10. run_jarvis.bat
echo.
echo Testes online opcionais:
echo   run_public_data_online_test.bat
echo   run_research_test.bat
echo.
echo Memoria semantica opcional:
echo   install_semantic_memory_optional.bat
echo.
echo Inicializacao automatica opcional:
echo   install_startup.bat
echo.
pause
