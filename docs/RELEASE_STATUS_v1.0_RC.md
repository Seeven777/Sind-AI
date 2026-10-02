# Jarvis Next 1.0 RC2 — Status

## Núcleo — implementado

- bootstrap
- lifecycle
- single instance
- SQLite WAL
- migrations
- structured logs
- Event Bus
- Task Engine
- checkpoints
- crash recovery
- health
- artifacts
- approvals
- policy engine
- independent verification

## Brain — implementado

- Ollama provider
- OpenAI-compatible optional provider
- Model Registry
- Model Router
- Model Mesh metadata
- conversation persistence
- Intent Router
- generic Tool Planner
- dynamic Mission Planner

## Agentes — implementado

- Research
- Analyst
- Creator
- Developer
- Operator
- Reviewer
- Inbox
- Memory Curator
- custom Agent Factory

## Research — implementado

- public web search
- public web fetch
- source collection
- source URLs in artifact
- network failure degradation

## Computer Use — implementado

- Playwright controller
- browser open/snapshot/fill/click
- Windows UI Automation
- list/inspect/activate/set-text/click
- WhatsApp Desktop executor
- approval + post-action evidence

Requires desktop extras to be installed on Windows.

## Connectors — implementado

- Local Inbox
- ICS Calendar
- Gmail read-only
- Google Calendar read-only
- durable connector items
- sync runs
- health
- optional OAuth

## Automation — implementado

- scheduler
- interval jobs
- one-time reminders
- condition watchers
- priority watcher
- calendar watcher
- file-change watcher
- Opportunity Engine
- startup briefing notification

## Knowledge — implementado

- working conversation context
- persistent typed memory
- provenance fields
- Memory Curator
- projects
- workspaces
- artifacts
- handoffs

## Capability Acquisition — implementado

- Skill Registry
- skill scaffold
- model-generated skill staging
- static safety guard
- tests before installation
- versioned install
- isolated runner
- Capability Resolver
- custom agents

## External ecosystems — implementado

- MCP stdio client
- MCP tool adapter
- remote agent HTTP adapter
- worker node registry
- remote worker server
- distributed dispatcher

## Voice — implemented adapter layer

- whisper.cpp STT
- Piper TTS
- health/degradation

Requires user-selected local binaries/models.

## UI — implementado

- Companion
- Jarvis HQ
- Mission Control
- Agent Directory
- Projects
- Memory
- System

## Agency Agents / Codex bridge — implementado

- autodiscovery de `~/.codex/agents/*.toml`
- parsing nativo TOML (`name`, `description`, `developer_instructions`)
- registro dinâmico de especialistas no AgentRegistry
- AgentRouter para seleção determinística de especialistas
- integração opcional com `divisions.json`
- integração opcional com `strategy/runbooks.json` / NEXUS
- execução explícita de equipes via `agency-run`
- especialistas importados sem ferramentas/permissões de Operator
- Agent Directory completo sem poluir o HQ principal
- falha/degradação segura quando Agency Agents não está instalado

## External configuration required

These are implemented but cannot become `healthy` until their external dependency exists:

- Google — OAuth credentials + user authorization
- WhatsApp — WhatsApp Desktop running + pywinauto
- Browser — Playwright + Chromium
- Windows UIA — pywinauto/Windows
- Voice — whisper.cpp/Piper binaries and models
- MCP — configured MCP server
- A2A/remote worker — second endpoint
- cloud models — endpoint/model/API secret

Their absence must never prevent Jarvis startup.

## Release gate

The release package is accepted only after:

- compileall
- pytest
- import-all
- deterministic product smoke
- repeated boot/reopen test
- ZIP integrity validation

Windows-specific live validation is performed by `Validate-Jarvis-Complete.cmd`.
