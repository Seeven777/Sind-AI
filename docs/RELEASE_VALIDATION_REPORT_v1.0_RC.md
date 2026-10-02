# Jarvis Next 1.0 RC2 — Release Validation Report

**Version:** 1.0.0rc2  
**Package:** Jarvis-Next-v1.0-RC2-Agency-Bridge-Full.zip

## Automated validation performed in the build environment

- Python compileall: PASS
- pytest: 62/62 PASS
- Package import sweep: 128 modules, 0 failures
- Release self-test: PASS
- Foundation stress: PASS
  - 50 clean boots
  - 10,000 persisted tasks
  - 100,000 persisted events
- Product runtime boot loop: PASS
  - 20 clean product-runtime boots

## Release self-test coverage

- Foundation startup/shutdown
- durable connectors
- typed memory
- projects
- custom Agent Factory
- generic Tool Planner
- approval → real file write → verification
- dynamic multi-agent mission
- artifact handoffs and Reviewer verdict
- model-generated skill staging
- skill tests, install and isolated execution
- scheduler and one-time reminder
- Opportunity Engine
- Jarvis HQ state
- Capability Resolver
- distributed node registry
- primary UI surfaces
- Agency/Codex TOML catalog loading
- deterministic specialist routing
- explicit specialist mission + Reviewer handoff
- Agent Directory visibility while preserving the 8-agent HQ core
- synthetic scale test: 282 Codex TOMLs loaded with unique IDs and working routing

## Implemented but dependent on the target Windows environment

These code paths require live target-environment validation:

- Ollama/Qwen inference
- Playwright/Chromium
- Windows UI Automation / pywinauto
- WhatsApp Desktop UI Automation
- Google OAuth, Gmail and Google Calendar
- Piper and whisper.cpp
- external MCP servers
- remote A2A/worker nodes
- optional cloud/OpenAI-compatible providers

`Validate-Jarvis-Complete.cmd` is the Windows release gate for these integrations.

## Degradation contract

Optional integrations are not allowed to stop the Core from booting. Expected
non-fatal states include `unconfigured`, `unavailable`, `authorization_required`,
`not_running`, and empty external registries.

## Security invariants

- External writes require policy authorization.
- Financial and credential actions are blocked by default.
- No tool success without execution evidence.
- Operator has an independent goal-verification layer.
- Generated skills are staged outside the Core and tested before installation.
- `web.fetch` blocks loopback/private/link-local/reserved destinations.
- Google tokens and generic secrets use Windows DPAPI on Windows.
- Remote worker exposure outside localhost requires a token.
- Local-only mode removes external network capabilities.

## Windows acceptance sequence

1. `Setup-Jarvis-Complete.cmd`
2. `Validate-Jarvis-Complete.cmd`
3. `Start-Jarvis.cmd`
4. Optional: `Connect-Google.cmd`
5. Optional: configure Piper/whisper.cpp
6. Optional: `Install-Jarvis-Startup.cmd`

A failed live integration must remain a specific integration defect. It must not be
reported as success, and it must not make the whole Jarvis unusable.
