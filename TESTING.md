# Testes e validação

## Comandos rápidos

```powershell
.\.venv\Scripts\python.exe .\foundation_regression_test.py
.\.venv\Scripts\python.exe .\cognitive_test.py
.\.venv\Scripts\python.exe -m unittest tests.test_habitat_ui_contract -v
node --check ui\web\app.js
node --check ui\web\orb.js
```

## Contratos críticos

- Uma ação sem verificação positiva não pode terminar como sucesso.
- Falhas do executor e falhas do verificador são casos diferentes.
- O WhatsApp exige evidência da mensagem de saída na conversa correta.
- Alterações do estado do backend devem aparecer no estado visual do orb.
- A UI deve continuar utilizável com movimento reduzido e qualidade baixa.

## QA visual

A tela idle foi renderizada em 1440×900 com navegador Chromium local. A validação cobre ausência de sidebar permanente, orb central, telemetria discreta, composer compacto e contraste em fundo escuro.
