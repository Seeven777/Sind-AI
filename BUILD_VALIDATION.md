# Build Validation — Jarvis Autonomous Operations 0.9

## Resultado do build

- Python compileall: **OK**
- JavaScript `ui/web/app.js`: **OK**
- `self_test.py`: **OK**
- `foundation_regression_test.py`: **OK**
- `institutional_test.py`: **OK**
- `autonomous_operations_test.py`: **OK**
- `team_portal_test.py`: **OK**
- Action IDs únicos: **OK**
- Referências Action → Workflow: **OK**
- Connector preview sem exigir/expor segredo: **OK**
- PBKDF2 local de usuários: **OK**
- Knowledge gap sem alucinação no portal: **OK**
- File monitor detecta mudança: **OK**
- Approval callback: **OK**
- Reagendamento após rejeição: **OK**
- UI operacional nova: **OK**

## Escala

- Public capabilities: 237
- Actions: 611
- Workflows: 474
- Total brokered: 1322

A 0.8 tinha 480 Actions + 409 Workflows. A 0.9 possui 611 Actions + 474 Workflows:
**196 novas possibilidades catalogadas** além da base anterior.

## Novos engines

- automations: 24
- monitors: 19
- approvals: 14
- connectors: 24
- team: 37
- notifications: 13

## Testes dependentes do Windows / ambiente real

Não são considerados validados pelo ambiente Linux de empacotamento:

- `run_routing_test.bat` — depende de pywinauto/Windows;
- `run_browser_test.bat` — abre Edge/Chrome real;
- `run_health_test.bat` — verifica Ollama/Windows/rede;
- `run_research_test.bat` — usa internet;
- `run_online_test.bat` — usa internet/APIs públicas;
- WordPress real — depende de perfil/credencial do usuário.

Esses testes devem ser executados no computador de testes após `install.bat`.

## Segurança verificada no código

- Team Portal: localhost por padrão.
- Connector Gateway: HTTPS only.
- Connectors: disabled por padrão.
- Secrets: keyring.
- `connector.preview`: usa placeholders `<secret>`.
- Action history: mascara password/token/secret/api_key.
- Scheduled Skills: exigem Approval Queue.
- Ações high/critical agendadas: Approval Queue.
- Rejeição/expiração de uma execução recorrente não deixa o job preso indefinidamente.
