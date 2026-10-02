# Jarvis Next — Base Horizontal v0.3

## Funcionando

- Foundation durável
- SQLite/migrations/recovery
- Event Bus
- Model Registry/Router
- Ollama provider
- Jarvis Orchestrator
- conversas persistentes
- memória básica
- Agent Registry
- Research Agent operacional
- task delegation
- Artifact Store
- verificação básica
- Tool Registry
- Policy Engine
- approvals base
- HQ logical projection
- **HQ web visual local**
- activity timeline
- “needs you”/attention projection
- CLI chat/doctor/demo

## Planejado e já com boundary arquitetural

Analyst, Creator, Developer, Operator, Reviewer, Inbox, Memory Curator avançado, browser, Windows UIA, MCP, A2A, Gmail, Calendar, WhatsApp, Scheduler, Watchers, Morning Briefing, Companion PySide/QML, Voice, Skills e Distributed Workers.

## Primeiro fluxo completo

`Usuário → Jarvis → Intent Router → Task Engine → Research → Model Router → Ollama → Artifact → Verify → Complete → Jarvis → HQ/Event timeline`

## HQ

O renderer atual é propositalmente leve. Ele define o contrato visual e já permite evoluir o escritório sem acoplar a lógica do sistema à UI.
