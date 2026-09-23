# Build Validation — Jarvis Personal GPT 1.7

## Novos testes

### `long_horizon_test.py`

Validado:

- criação de job persistente;
- planejamento em etapas;
- execução isolada por checkpoint;
- conclusão e progresso 100%;
- checkpoints persistidos;
- retomada automática de etapa segura após reinício;
- bloqueio de retomada automática de etapa com possível efeito externo.

### `institutional_workspace_test.py`

Validado:

- Instagram resolvido para aba embutida;
- Dashboard lido pelo adapter da aba;
- nove serviços cotidianos registrados;
- perfil persistente do navegador institucional;
- exclusão permanente de conversa;
- remoção de anexo exclusivo da conversa;
- preservação de anexo de projeto;
- UI de exclusão de chat presente.

## Regressões

Passaram novamente:

- Capability Acquisition;
- Swarm + Apprenticeship;
- Long-Running Runtime;
- UX Stability;
- Personal GPT;
- Cognitive Foundation;
- Self Awareness;
- Foundation Regression;
- Self Test.

Resumo preservado:

- 237 capabilities públicas;
- 611 Actions;
- 474 Workflows;
- 1322 recursos brokered.

## Frontend

- `ui/web/app.js`: sintaxe OK;
- `mobile/web/app.js`: sintaxe OK;
- `npm run build`: OK;
- Vercel continua distribuindo somente o launcher estático.

## Limitação do ambiente de build

O ambiente Linux usado para empacotamento não possui PySide6 instalado, portanto a renderização visual real das novas abas Qt WebEngine precisa ser validada no Windows após `install.bat`. Os arquivos Python passaram em `compileall`; as integrações não-Qt e regressões passaram offline.
