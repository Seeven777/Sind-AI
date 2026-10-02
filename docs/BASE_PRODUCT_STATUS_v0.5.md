# Jarvis Next — Base Horizontal v0.5

## Objetivo

Ter a maior parte do produto representada por contratos estáveis enquanto alguns fluxos já funcionam de ponta a ponta.

## Agentes operacionais

1. Research — LLM + artifacts
2. Analyst — LLM + artifacts
3. Creator — LLM + artifacts
4. Developer — LLM + artifacts
5. Operator — ferramentas reais + política + evidência
6. Reviewer — LLM + artifacts
7. Memory Curator — auditoria determinística da memória

Planejado:
- Inbox — aguarda connectors

## Operator

Ferramentas atuais:

- `system.time` — READ — automático
- `files.read_text` — READ — automático
- `files.list_directory` — READ — automático
- `files.write_workspace_text` — INTERNAL_WRITE — exige aprovação

Escrita é limitada a:

`%LOCALAPPDATA%\JarvisNext\workspace_files`

Nenhuma ferramenta desta versão altera o core do Jarvis.

## Aprovação

Fluxo:

```text
pedido
→ Operator
→ Policy Engine
→ approval.required
→ HQ mostra "Precisa de você"
→ Aprovar / Rejeitar
→ execução
→ verificação
→ task concluída
```

## HQ

O protocolo permanece `jarvis.hq.snapshot.v2` para preservar compatibilidade; a v0.5 adiciona campos e ações sem quebrar o contrato existente.

A interface continua sem Node e sem engine 3D. Ela representa um escritório estilo game em HTML/CSS e consome apenas estado real do backend.

Isso preserva a possibilidade de trocar o renderer por Three.js/QML/WebGPU depois sem alterar o Core.

## Próximos grandes blocos

- Connector Registry real
- Gmail/Calendar read-only
- Inbox Agent
- Morning briefing com dados externos
- Scheduler + Watchers
- browser estruturado
- Windows UI Automation
- voz
- skills
- MCP/A2A
