# Agency Agents / Codex Bridge

## Objetivo

Integrar ao Jarvis Next as definições de especialistas instaladas pelo projeto `agency-agents`, sem tratá-las como centenas de modelos independentes e sem ampliar permissões de execução.

## O que o Jarvis detecta

Por padrão:

```text
%USERPROFILE%\.codex\agents\*.toml
```

Cada TOML Codex deve conter:

```toml
name = "..."
description = "..."
developer_instructions = "..."
```

O diretório pode ser sobrescrito por:

```text
JARVIS_CODEX_AGENTS_DIR
```

## Metadados NEXUS

Jarvis tenta localizar o repositório `agency-agents` em caminhos usuais, incluindo o Desktop do usuário e um diretório irmão do projeto Sind-AI.

Também pode ser definido explicitamente:

```text
JARVIS_AGENCY_AGENTS_ROOT
```

Quando presente, Jarvis lê:

```text
divisions.json
strategy/runbooks.json
```

Isso permite identificar divisões e equipes NEXUS sem duplicar o catálogo dentro do Core.

## Segurança

Uma definição Agency importada vira um `ArtifactAgent` de conhecimento. Ela recebe:

- missão;
- contexto do agente anterior;
- modelo escolhido pelo Model Router.

Ela **não recebe ferramentas**.

Logo, uma instrução externa não consegue, por si só:

- escrever arquivos;
- abrir janelas;
- enviar WhatsApp;
- clicar na interface;
- navegar em browser;
- usar credenciais;
- declarar uma ação física como concluída.

Ações reais continuam passando por:

```text
Jarvis -> Operator -> Policy Engine -> ToolExecutor -> Observe/Act/Verify
```

## Roteamento

`AgentRouter` consulta o catálogo Agency e classifica especialistas de forma determinística usando:

- nome;
- slug;
- descrição;
- divisão;
- termos do objetivo.

Por padrão, uma missão automática adiciona no máximo um especialista Agency ao pipeline central para manter custo/latência previsíveis.

Exemplo conceitual:

```text
Research
-> Analyst
-> Agency Backend Architect
-> Developer
-> Reviewer
```

## Runbooks

Listar:

```powershell
.\.venv\Scripts\python.exe -m jarvis agency-runbooks
```

Executar apenas grupos `activation=always`:

```powershell
.\.venv\Scripts\python.exe -m jarvis agency-run marketing-campaign "Planeje uma campanha de Instagram"
```

Incluir todos os grupos do runbook:

```powershell
.\.venv\Scripts\python.exe -m jarvis agency-run marketing-campaign "Planeje uma campanha de Instagram" --all-groups --max-agents 0
```

`--max-agents 0` remove o limite de especialistas. O Reviewer central do Jarvis é anexado ao final.

## Diagnóstico

```powershell
.\.venv\Scripts\python.exe -m jarvis agency-status
.\.venv\Scripts\python.exe -m jarvis agency-agents --limit 20
.\.venv\Scripts\python.exe -m jarvis agency-route "Implemente uma API backend em Python"
```

## Degradação

Se `~/.codex/agents` ou o repositório Agency não existir, o Core continua inicializando normalmente. A integração aparece como `unavailable`, mas os 8 agentes centrais continuam operacionais.
