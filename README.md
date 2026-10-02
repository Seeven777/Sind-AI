# Jarvis Next 1.0 RC2
## Personal Agent Operating System

Jarvis Next é um sistema pessoal de agentes local-first para Windows.

A arquitetura foi construída para que o usuário converse com **Jarvis**, enquanto agentes especializados, ferramentas, conectores e modelos trabalham por trás.

## Instalação

Extraia o conteúdo diretamente sobre a raiz do repositório:

`C:\Users\AMD\Desktop\Sind-AI`

Preserve:

- `.git`
- `.venv` se já existir

Instalação completa:

`Setup-Jarvis-Complete.cmd`

Validação completa:

`Validate-Jarvis-Complete.cmd`

Abrir Jarvis:

`Start-Jarvis.cmd`

HQ:

`Start-Jarvis-HQ.cmd`

## Superfícies

- `/` — Companion
- `/hq` — escritório de agentes
- `/mission-control` — tarefas, handoffs, approvals e evidências
- `/agents` — Agent Directory
- `/projects` — projetos
- `/memory` — memória persistente
- `/system` — modelos, connectors e infraestrutura

Servidor padrão:

`http://127.0.0.1:4760`

## Agentes built-in

- Research
- Analyst
- Creator
- Developer
- Operator
- Reviewer
- Inbox
- Memory Curator

Também existe `AgentFactory` para agentes customizados persistentes.

## Agency Agents / Codex

Jarvis detecta automaticamente especialistas Codex instalados em:

`%USERPROFILE%\.codex\agents\*.toml`

Quando o repositório `agency-agents` também está disponível, Jarvis lê `divisions.json` e `strategy/runbooks.json` para enriquecer divisão, roteamento e equipes NEXUS. O caminho pode ser sobrescrito por `JARVIS_AGENCY_AGENTS_ROOT`.

Esses arquivos são **definições de especialistas, não modelos de IA separados**. Todos reutilizam o Model Mesh do Jarvis. Especialistas importados não recebem ferramentas de execução: ações reais continuam restritas ao Operator, Policy Engine e verificação independente.

Comandos úteis:

```powershell
.\.venv\Scripts\python.exe -m jarvis agency-status
.\.venv\Scripts\python.exe -m jarvis agency-agents --limit 20
.\.venv\Scripts\python.exe -m jarvis agency-route "Implemente uma API backend em Python"
.\.venv\Scripts\python.exe -m jarvis agency-runbooks
.\.venv\Scripts\python.exe -m jarvis agency-run marketing-campaign "Planeje uma campanha de Instagram"
```

O Agent Directory (`/agents`) mostra o catálogo completo detectado. O escritório principal (`/hq`) permanece com os 8 agentes centrais para não ficar visualmente sobrecarregado.

## Primeiros comandos

```text
Pesquise informações atuais sobre ...
Monte uma equipe de agentes e desenvolva ...
Implemente um script Python para ...
Resuma minha caixa de entrada
Me dê meu briefing do dia
Que horas são?
Liste a pasta C:\
Organize sua memória
Abra o site openai.com
Liste as janelas abertas
Envie uma mensagem no WhatsApp para Nome: mensagem
```

Ações com efeito externo passam pelo Policy Engine.

## Ferramentas reais

### Local

- `system.time`
- `files.read_text`
- `files.list_directory`
- `files.write_workspace_text`
- Windows UI Automation
- skills

### Web/browser

- `web.search`
- `web.fetch`
- `browser.open`
- `browser.snapshot`
- `browser.fill`
- `browser.click`

### Comunicação

- `whatsapp.send_message`
- Gmail read-only
- Google Calendar read-only

### Ecossistema

- MCP stdio
- A2A/remote agents
- worker nodes
- skills versionadas

## Google

Coloque sua credencial OAuth desktop em:

`%LOCALAPPDATA%\JarvisNext\config\google_client.json`

Depois:

`Connect-Google.cmd`

Gmail e Google Calendar são read-only.

Tokens são protegidos com Windows DPAPI.

## Computer Use

Instalado por:

`Setup-Jarvis-Extras.cmd`

Backends:

- Playwright/Chromium
- pywinauto UI Automation

A prioridade arquitetural é:

API > structured integration > browser DOM > Windows UIA.

## WhatsApp Desktop

O envio usa Windows UI Automation.

Fluxo:

```text
pedido
→ Operator
→ approval.required
→ você aprova
→ abre/localiza WhatsApp
→ contato
→ campo de mensagem
→ envio
→ observa a mensagem na conversa
→ somente então declara sucesso
```

## Voz

A camada de voz é local e opcional:

- STT: whisper.cpp
- TTS: Piper

Veja `docs/VOICE_SETUP.md`.

Nenhum backend de voz pode impedir o Core de iniciar.

## Skills

Criar scaffold:

```powershell
.\.venv\Scripts\python.exe -m jarvis skill-scaffold demo.skill --description "..."
```

Gerar uma skill com o modelo local:

```powershell
.\.venv\Scripts\python.exe -m jarvis skill-generate demo.skill --description "..."
```

Instalar somente após testes:

```powershell
.\.venv\Scripts\python.exe -m jarvis skill-install "CAMINHO"
```

Skills ficam fora do Core, versionadas e reversíveis.

## Proatividade

Jarvis possui:

- Scheduler persistente
- Watchers
- reminders
- file watchers
- connector sync
- Opportunity Engine
- briefing
- startup com Windows

Configurar início automático:

`Install-Jarvis-Startup.cmd`

Remover:

`Remove-Jarvis-Startup.cmd`

## Local Only

Para impedir acesso externo:

```powershell
$env:JARVIS_LOCAL_ONLY="1"
```

ou em:

`%LOCALAPPDATA%\JarvisNext\config\config.toml`

```toml
[privacy]
mode = "local_only"
```

Neste modo, Jarvis remove do Tool Mesh:

- web
- browser externo
- Google
- WhatsApp
- MCP remoto
- A2A remoto
- cloud models

Arquivos, memória, agentes e modelos locais continuam disponíveis.

## Model Mesh

Padrão:

- Ollama
- `qwen3.5:4b`

Providers OpenAI-compatible podem ser conectados opcionalmente sem alterar agentes.

O Core continua local-first.

## Distributed Jarvis

Iniciar worker:

```powershell
.\.venv\Scripts\python.exe -m jarvis worker --host 127.0.0.1 --port 4770
```

Registrar node remoto:

```powershell
.\.venv\Scripts\python.exe -m jarvis node-add node2 "PC 2" http://IP:4770 --capability coding
```

## Constituição

1. **Sem ação real, não houve execução.**
2. **Sem evidência, não houve sucesso.**
3. **Sem checkpoint, não há tarefa durável.**
4. **Sem fonte, não é memória confiável.**
5. **Sem permissão, não há efeito externo.**
6. **Nenhuma função opcional pode impedir o Jarvis de iniciar.**
7. **Jarvis pode criar skills; não pode modificar seu próprio Core em produção.**

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest
```

A validação de release também executa smoke tests, UI routes e APIs locais.

Consulte `docs/RELEASE_STATUS_v1.0_RC.md`.
