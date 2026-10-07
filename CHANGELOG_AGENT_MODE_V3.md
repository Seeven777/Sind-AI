# Agent Mode Life v3

## Presence / Jarvis Core
- Rebuilt the main Jarvis orb as a custom WebGL2 particle membrane.
- Visual language combines a dark living core, point-cloud sphere and restrained electric filaments.
- The core reacts to IDLE, LISTENING, THINKING, RESEARCHING, EXECUTING, VERIFYING, SPEAKING, SUCCESS, ATTENTION and ERROR.
- Mouse/pointer and voice amplitude affect the core without turning it into decorative HUD noise.
- Canvas2D fallback is included when WebGL2 is unavailable.

## Agent life
- Added a real recurring `agent_life_cycle` (default: every 20 minutes while Jarvis is running).
- Inbox, Memory Curator, Analyst, Creator, Developer, Operator and Reviewer now receive real background work.
- Research remains responsible for the separate autonomous curiosity cycle.
- One agent failing no longer prevents the remaining agents from working.
- Agent state is based on persisted execution truth; no fake activity is generated.

## Recovery / status
- Local model artifact agents retry one recoverable bad/empty generation before failing.
- A past failed run no longer leaves an agent visually broken forever.
- Idle agents show READY/available state instead of fake `0%` progress.
- HQ reports degraded health separately from current execution state.

## Self-improvement foundations
- Authorized connectors are synchronized before Inbox triage.
- The autonomous cycle inventories registered capabilities for Analyst context.
- Operator receives only verified low-risk read-only autonomous checks; PolicyEngine remains the authority gate.
- Memory Curator now identifies old low-importance memories as archive candidates without deleting them automatically.
- Reviewer criteria include objective coverage, artifacts, execution evidence, stage coherence, tests and unsupported claims.
- Developer instructions now require a structured execution plan when an actual operation is needed.

## Validation
- Python suite: 96 tests passing.
- Release self-test: PASS across foundation, product boots, connectors, memory, projects, agents, approval/verification, dynamic missions, skills, scheduler, HQ, distributed registry and UI surfaces.
- HQ JavaScript syntax: PASS.
