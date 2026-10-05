# Jarvis Next RC5 — Product Upgrade

RC5 is the product-oriented evolution of RC4. The goal is not simply more screens; it is a clearer personal-agent operating system with a usable daily Companion, an interactive spatial HQ, stronger memory ergonomics, and better artifact creation.

## What changed

### Companion
- Fixed chat-thread scrolling with a real flex scroll container and persistent scrollbar.
- Added a “jump to latest” control when the user scrolls away from the bottom.
- Improved message typography, Markdown rendering, code blocks and tables.
- Added explicit “Memorizar” action on assistant responses.
- Added memory-aware UI, attachments and persistent conversation management.
- Refined hierarchy, density, spacing and visual feedback.

### HQ / Spatial Office
- Replaced the external Three.js runtime dependency with a zero-dependency perspective renderer.
- The office remains genuinely interactive: orbit, zoom, selection, department focus and labels.
- Adds spatial rooms, command core, desks, screens, plants, chairs, workers, status lights and system network links.
- Backend is the source of truth; the scene never invents agent state.

### Mission Control
- Added top-level operational counters.
- Added progress percentage per mission.
- Added explicit Approve / Reject controls.
- Added real Event Bus feed from `/api/events`.
- Kept pipeline, attention and tool-run views.

### Memory
- Added direct “remember” workflow.
- Added “forget” action.
- Memory mutations stay on the SQLite owner thread through the HTTP bridge.

### Operational artifacts
- Added `files.write_workspace_pdf`.
- PDF output is created only inside the Jarvis workspace.
- Operator verifies that the PDF exists, has pages and matches its SHA-256 execution evidence.
- Tool Planner can select the PDF tool when available.

### Research robustness
- Search now tries DuckDuckGo first and a public Bing HTML fallback.
- Research expands targeted queries for SindPetshop-SP when the objective mentions it.
- Research receives the current system date and is explicitly prohibited from inventing dates, numbers, names or document status.

## Validation

- Full pytest suite: 87 passed
- Python compileall: PASS
- Companion JS syntax: PASS
- HQ JS syntax: PASS
- Mission Control JS syntax: PASS

## Safety invariants preserved

- No external agent receives Operator permissions implicitly.
- Physical actions remain under Policy / Approval / Operator / Verification.
- SQLite thread affinity is not weakened with `check_same_thread=False`.
- External services remain optional.
