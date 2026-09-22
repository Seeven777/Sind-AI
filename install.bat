@echo off
cd /d "%~dp0"

echo.
echo ===============================================
echo  JARVIS PERSONAL GPT 1.2 - EXPERIENCE + MOBILE
echo ===============================================
echo.
echo GPT pessoal local - sem API paga obrigatoria.
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
echo TESTES RECOMENDADOS:
echo   1. run_doctor.bat
echo   2. run_personal_gpt_test.bat
echo   3. run_mobile_companion_test.bat
echo   4. run_cognitive_test.bat
echo   5. run_self_test.bat
echo   6. run_foundation_test.bat
echo   7. run_model_router_test.bat
echo   8. run_routing_test.bat
echo   9. run_health_test.bat
echo  10. run_browser_test.bat
echo  11. run_jarvis.bat
echo.
echo ACESSO MOBILE:
echo   - abra o Jarvis e clique em "Jarvis Mobile"
echo   - se o Windows bloquear a rede local, execute enable_mobile_access.bat
echo   - conecte o celular a mesma rede Wi-Fi
echo.
pause
