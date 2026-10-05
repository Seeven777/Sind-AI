# Jarvis Next RC4 — Product Vision

## Objetivo

RC4 trata o Jarvis como um produto de software completo, não como uma coleção de scripts. A prioridade é unir uma fundação durável a uma experiência visual que comunique claramente o estado real do sistema.

## Camadas

### Foundation
- SQLite com afinidade de thread preservada.
- migrations versionadas.
- configurações persistentes.
- tarefas, checkpoints, memória e eventos duráveis.
- shutdown/recovery previsíveis.

### Intelligence
- Model Registry / Model Router.
- Ollama local-first.
- Nemotron remoto opcional.
- Hermes como executor consultivo separado.
- Agency Agents como especialistas.

### Action
- Tool Registry.
- Policy Engine.
- Approvals.
- Operator.
- Observe → Act → Observe → Verify.

### Product
- Companion.
- Conversation history.
- search / rename / pin / archive / delete.
- export / regenerate / edit / copy.
- file attachments de texto.
- modos Auto / Rápido / Deep / Hermes.
- preferências persistentes.
- command palette.
- ditado pelo navegador quando suportado.
- launcher em janela de aplicativo.

### Operations UI
- Mission Control.
- Agents.
- Projects.
- Memory.
- System.
- AI Mesh status.

### Visual OS
- HQ 3D interativo.
- departamentos reais como espaços.
- agentes como estações.
- iluminação e status derivados do backend.
- seleção de agente/departamento.
- inspeção contextual.
- fallback `/hq-classic`.

## Critério de qualidade

A UI pode ser sofisticada sem virar fonte de verdade. Estados visuais devem ser projeções dos serviços do backend.

O sistema pode estar visualmente avançado, mas nunca pode afirmar que uma ação física ocorreu sem evidência produzida pelo mecanismo de execução/verificação.
