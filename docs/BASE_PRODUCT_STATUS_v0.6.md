# Jarvis Next — Base Horizontal v0.6

## Mudança principal

Jarvis agora possui uma camada de observação contínua real e durável.

### Agentes operacionais

- Research
- Analyst
- Creator
- Developer
- Operator
- Reviewer
- Memory Curator
- Inbox

Todos os oito Agent Cards do escritório já possuem runtime real.

## Connectors reais desta versão

### Caixa de entrada local

Pasta:

`%LOCALAPPDATA%\JarvisNext\connectors\inbox`

Arquivos colocados nela viram itens observáveis.

Formatos textuais recebem conteúdo; outros arquivos ainda geram metadados.

É read-only: Jarvis não altera os arquivos de origem.

### Calendário ICS

Arquivo:

`%LOCALAPPDATA%\JarvisNext\connectors\calendar.ics`

VEVENTs são convertidos em itens de calendário.

Também é read-only.

## Por que começar local

Essa camada permite validar sincronização, priorização, watchers, briefing e Inbox Agent sem depender de OAuth, contas ou serviços pagos.

Gmail e Google Calendar futuramente apenas implementam o mesmo contrato `Connector`.

## Scheduler

Jobs duráveis padrão:

- `connector.sync_all` — a cada 5 minutos;
- `watchers.check` — a cada 2 minutos.

Enquanto `Start-Jarvis.cmd` está rodando, o servidor executa ticks a cada 30 segundos e dispara apenas jobs vencidos.

## Watchers

Dois watchers iniciais:

- novos itens com prioridade >= 80;
- eventos de calendário dentro de 180 minutos.

Watchers emitem eventos, não executam efeitos externos.

## Briefing

O briefing usa agora:

- tasks;
- approvals;
- artifacts;
- inbox;
- calendar;
- connector health;
- watchers;
- missions.

## Estado da arquitetura

Ativo:
- Core
- Task Engine
- Event Bus
- Memory
- Model Mesh base
- Tool Mesh
- Agent Office
- Approvals
- Connectors
- Scheduler
- Watchers
- Briefing
- Inbox Agent

Próximo:
- Gmail read-only
- Google Calendar read-only
- browser estruturado
- Windows UI Automation
- voice
- skill acquisition
- MCP / A2A
- serviço de inicialização com Windows
