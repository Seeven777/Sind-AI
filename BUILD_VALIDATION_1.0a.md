# Build Validation — Jarvis Cognitive Foundation 1.0a

## Resultado

Validação offline executada após a reconstrução cognitiva e a limpeza visual.

- Python compileall: **OK**
- JavaScript `ui/web/app.js`: **OK**
- `cognitive_test.py`: **OK**
- `self_test.py`: **OK**
- `foundation_regression_test.py`: **OK**
- `institutional_test.py`: **OK**
- `autonomous_operations_test.py`: **OK**
- `team_portal_test.py`: **OK**
- `catalog_routing_test.py`: **OK**

## Cognitive Core validado

- conversa persistente em SQLite;
- recuperação FTS5 entre conversas;
- aprendizado explícito de preferências/correções;
- memória semântica opcional e desligada por padrão;
- normalização correta do endpoint base do Ollama para embeddings;
- 28 fontes no Public Data Registry;
- prioridade de IBGE, DataJud, MTE, Banco Central e Dados Abertos SP conforme o assunto;
- Context Window reduzido por seleção de ferramentas sob demanda.

## Interface validada

- histórico de conversas;
- chat central;
- inspector reduzido a Contexto / Fontes / Atividade;
- Centro de Controle em overlay;
- páginas permanentes de Actions, Workflows, Automações, Monitores e Connectors removidas da navegação principal;
- os backends correspondentes continuam ativos e cobertos pelos testes legados.

## Infraestrutura herdada validada

Os testes antigos confirmam que a simplificação da interface não removeu:

- 237 public capabilities;
- 611 actions;
- 474 workflows;
- Research Engine;
- Browser Agent;
- Knowledge Base;
- Institutional Intelligence;
- Training;
- Content Operations;
- Governance;
- Automations/Monitors/Approvals;
- Connectors;
- Team Portal.

## Testes que precisam do Windows/internet real

`routing_regression_test.py` não pode rodar no ambiente Linux de empacotamento porque `pywinauto` é específico da stack Windows do Jarvis. Execute `run_routing_test.bat` no computador de testes.

`public_data_online_test.py` foi preparado, mas o ambiente de empacotamento atual não possui resolução DNS de saída. Execute `run_public_data_online_test.bat` no computador de testes para verificar IBGE, Crossref e Dados.gov.br na rede real.

A memória semântica é opcional. Ela só deve ser testada após `install_semantic_memory_optional.bat`, que baixa o modelo de embeddings no Ollama.
