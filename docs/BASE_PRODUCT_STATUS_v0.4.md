# Jarvis Next — Base Horizontal v0.4

## Mudança principal

A base agora possui um caminho multiagente completo e uma UI local unificada.

### Fluxo real

```text
Usuário
  ↓
Jarvis
  ↓
Task / Mission
  ↓
Research
  ↓ artifact
Analyst
  ↓ artifact
Creator
  ↓ artifact
Reviewer
  ↓ review
Verification
  ↓
Entrega
```

Research, Analyst, Creator e Reviewer usam o mesmo Model Mesh.
Isto NÃO significa quatro modelos simultâneos.

## UI

`Start-Jarvis.cmd` sobe uma única instância do Product Runtime e abre o Companion.

- `/` Companion minimalista
- `/hq` Jarvis HQ
- `/api/chat`
- `/api/hq`
- `/api/briefing`
- `/api/health`
- `/api/mission/team`

A UI é uma projeção. O banco e o Event Bus continuam sendo a fonte de verdade.

## Agent Office

O projeto `agent-office-main.zip` enviado pelo usuário foi usado como referência conceitual para:
- escritório como projeção do backend;
- workers com status real;
- atividade visível;
- agentes que precisam de intervenção;
- separação entre runtime e renderer.

O código do projeto externo não é necessário para executar Jarvis v0.4.

## Base horizontal atual

ATIVO:
- Foundation
- Task Engine
- Event Bus
- Recovery
- Model Provider/Registry/Router
- Jarvis
- Research
- Analyst
- Creator
- Reviewer
- Conversation persistence
- Memory base
- Artifact Store
- Mission pipeline
- Workspaces base
- Policy Engine
- Tool Registry
- Briefing local
- Companion web de desenvolvimento
- HQ visual de desenvolvimento

ESTRUTURADO / PRÓXIMO:
- Developer
- Operator
- Inbox
- Memory Curator
- Playwright
- Windows UIA
- Connectors
- Gmail
- Calendar
- WhatsApp
- Voice
- Scheduler/Watchers
- MCP
- A2A
- Capability acquisition
- PySide/QML native shell
- 3D/isometric renderer avançado
