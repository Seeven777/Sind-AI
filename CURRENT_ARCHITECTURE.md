# Arquitetura atual auditada

Data da auditoria: 2026-10-01.

## Topologia confirmada

O repositório contém duas camadas integradas, sem substituição do runtime legado:

1. `jarvis_desktop.py` inicia o aplicativo PySide6, o tray, o hotkey, o `JarvisAgent`, o atualizador e o companion mobile.
2. `ui/habitat.py` hospeda a interface HTML em `QWebEngineView` e expõe operações por `QWebChannel`.
3. `core/agent.py` é hoje o composition root. Ele instancia memória, modelos, contexto, skills, capabilities, execução, pesquisa, automações, observação e supervisão.
4. `core/openjarvis_bridge.py` usa o OpenJarvis local em `127.0.0.1:8000` como núcleo conversacional opcional. O roteador Ollama anterior permanece como fallback.
5. `run_integrated_jarvis.py` e `Iniciar-Jarvis-Integrado.cmd` sobem o backend OpenJarvis, aguardam saúde e abrem o desktop.

## Execução e verificação

- O fluxo geral cria registros em `runtime/task_store.py`, registra eventos de ferramenta e encerra a tarefa como concluída, falha, pausa ou interrupção.
- `runtime/verifier.py` centraliza verificações para ferramentas comuns.
- `runtime/phase4/` contém o runtime de automação Windows e WhatsApp com UI Automation, observação e verificação específica.
- O WhatsApp usa verificação fail-closed: uma ação sem evidência positiva não deve ser promovida a sucesso.
- `runtime/diagnostics.py` recebe eventos e exceções com `task_id`.

## Memória e contexto

- `memory/store.py`: memórias explícitas e aliases em SQLite persistente.
- `cognitive/conversation_store.py`: conversas e sessões.
- `cognitive/semantic_memory.py`: recuperação semântica opcional.
- `cognitive/project_store.py`: contexto de projetos.
- `cognitive/context_orchestrator.py`: montagem de contexto por solicitação.
- Os dados persistentes ficam em `%USERPROFILE%/JarvisData`, separados do código da versão.

## Interface e voz

- A interface ativa é `ui/web/index.html`, carregada localmente pelo Qt WebEngine.
- `ui/web/app.js` recebe `statusChanged`, `commandFinished` e `snapshotChanged` do bridge.
- O worker do agente fica em `QThread`; a thread da UI não executa o modelo.
- Há pipelines de áudio/voz existentes, porém o bridge visual ainda não entrega níveis contínuos de amplitude do microfone ou TTS.

## Problemas e riscos encontrados

- `core/agent.py` concentra responsabilidades demais e é o maior ponto de acoplamento.
- Existem hubs e registries, mas não há um único contrato declarativo obrigatório para todas as ferramentas (`name`, schema, risco, `execute`, `verify`).
- O estado de UI era reduzido principalmente a `thinking` e `executing`; planejamento, observação e verificação existiam no runtime, mas não tinham representação visual própria.
- A UI anterior mantinha sidebar, cards e chat como composição permanente, em conflito com a direção visual.
- O identificador persistido por `TaskStore` é inteiro. Ainda não há um identificador público no formato `TASK-YYYYMMDD-NNN` em toda a aplicação.
- O Git atual mistura o checkout do OpenJarvis com muitos arquivos locais não rastreados. Atualizações por `git pull` direto apresentam risco alto de colisão.
- Há blocos defensivos `except Exception: pass` em rotinas de shutdown e serviços opcionais. Alguns são aceitáveis em cleanup, mas não devem ser usados no caminho de execução física.
- O fallback entre OpenJarvis e o roteador anterior preserva disponibilidade, mas duplica caminhos conversacionais e aumenta o custo de diagnóstico.

## Prioridades recomendadas

1. Extrair o composition root de `JarvisAgent` em módulos injetáveis sem reescrever os executores validados.
2. Padronizar um `ToolDescriptor` e adaptadores para ferramentas legadas.
3. Criar um event bus tipado entre runtime e UI, mantendo compatibilidade com os sinais Qt existentes.
4. Introduzir um `public_task_id` sem alterar as chaves SQLite atuais.
5. Cobrir cada ação mutável com verificação fail-closed e teste de falha.
6. Separar o fork local do upstream OpenJarvis em branch e registrar arquivos próprios no Git.

