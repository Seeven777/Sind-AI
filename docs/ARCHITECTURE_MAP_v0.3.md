# Jarvis Next — Architecture Map v0.3

```text
USER
 │
 ├─ Companion (boundary)
 ├─ Jarvis HQ (visual base active)
 └─ CLI (active)
       │
       ▼
JARVIS ORCHESTRATOR (active)
 │
 ├─ Intent Router (active)
 ├─ Memory (basic active)
 ├─ Task Engine (active)
 ├─ Approval/Policy (base active)
 │
 ├─ AGENT REGISTRY
 │    ├─ Research ........ ACTIVE
 │    ├─ Analyst ......... PLANNED
 │    ├─ Creator ......... PLANNED
 │    ├─ Developer ....... PLANNED
 │    ├─ Operator ........ PLANNED
 │    ├─ Reviewer ........ PLANNED
 │    ├─ Inbox ........... PLANNED
 │    └─ Memory Curator .. PLANNED
 │
 ├─ MODEL MESH
 │    ├─ Registry ........ ACTIVE
 │    ├─ Router .......... ACTIVE
 │    ├─ Ollama .......... ACTIVE
 │    └─ Cloud adapters .. BOUNDARY
 │
 ├─ TOOL MESH
 │    ├─ system.time ..... ACTIVE
 │    ├─ files.read_text . ACTIVE
 │    ├─ Browser ......... BOUNDARY
 │    ├─ Windows UIA ..... BOUNDARY
 │    ├─ MCP ............. BOUNDARY
 │    └─ A2A ............. BOUNDARY
 │
 ├─ ARTIFACT STORE ....... ACTIVE
 ├─ VERIFICATION ......... BASIC ACTIVE
 ├─ WORKSPACES ........... BOUNDARY
 ├─ PROJECTS ............. BOUNDARY
 ├─ CONNECTORS ........... BOUNDARY
 ├─ WATCHERS ............. BOUNDARY
 ├─ SCHEDULER ............ BOUNDARY
 ├─ BRIEFING ............. BOUNDARY
 ├─ VOICE ................ BOUNDARY
 ├─ SKILLS ............... BOUNDARY
 ├─ CAPABILITY RESOLVER .. BOUNDARY
 └─ DISTRIBUTED NODES .... BOUNDARY
```

## Regra

`ACTIVE` significa que existe ao menos um caminho executável/testável.
`BOUNDARY` significa que a arquitetura já possui local e contrato, mas ainda não declara capacidade que não existe.
`PLANNED` significa Agent Card visível no HQ, sem worker operacional.
