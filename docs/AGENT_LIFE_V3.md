# Agent Life v3

Jarvis now has two complementary autonomous rhythms:

1. **Curiosity** — Research explores arbitrary subjects, persists discoveries and decides whether they deserve attention.
2. **Agent life** — the remaining core roles periodically inspect and improve Jarvis' understanding of its own environment.

The default agent-life interval is 20 minutes and the first cycle is eligible as soon as the background runtime starts.

## Core roles in the cycle

- **Inbox** — synchronizes/triages authorized sources without replying or changing external data.
- **Memory Curator** — audits useful context, duplicates and conservative archive candidates.
- **Analyst** — reads health, recent alerts, discoveries, capabilities, Inbox and Memory signals.
- **Creator** — turns analysis into one small useful initiative.
- **Developer** — performs a maintenance inspection and identifies a concrete technical item to test/monitor.
- **Operator** — performs only allowlisted low-risk read operations through the normal PolicyEngine.
- **Reviewer** — independently checks whether the cycle was useful, supported and authorization-safe.
- **Research** — runs in the separate curiosity cycle.

The cycle is deliberately read/prepare-first. It does not silently grant source-code write authority to Jarvis.

## Truthful UI state

`working` means a persisted agent run is currently executing. Completed agents return to `idle`; a stale failure becomes `idle + degraded`, preserving evidence without visually disabling the agent forever. Progress exists only during an active run.
