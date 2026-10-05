# Release Validation — Jarvis Next 1.0 RC4

Validation executed against the consolidated RC4 working tree.

## Automated

- pytest: **85 passed**
- Python `compileall`: PASS
- Node syntax check: PASS for all HQ web JavaScript files
- DOM ID cross-check: PASS for Companion and HQ

## Product areas covered by tests

- conversation history
- conversation export
- auto conversation titles
- attachments
- Fast / Deep / Hermes modes
- persistent UI preferences
- AI Mesh integrations
- mission orchestration
- approvals and policy
- memory
- projects
- HQ thread affinity
- recovery / shutdown
- existing Agency bridge

## External services

Hermes, Nemotron, WA-AKG, Google and Creative Studio remain optional. Their absence must not prevent the local Jarvis core from starting.

## Visual architecture

HQ 3D uses Three.js through the browser, while `/api/hq` remains the source of truth. `/hq-classic` remains as fallback.
