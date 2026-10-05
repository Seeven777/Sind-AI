# Upgrade to Jarvis Next 1.0 RC3

## Recommended path

This upgrade is additive. It preserves the existing `.git`, `.venv` and local data directory.

```powershell
cd C:\Users\AMD\Desktop\Sind-AI
.\Stop-Jarvis.cmd
```

Extract the RC3 Full package over the project root and replace existing project files.

Then:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\Validate-Jarvis-Complete.cmd
.\Start-Jarvis.cmd
```

Expected validation:

```text
79 passed
```

## New surfaces

- Companion: `/`
- 3D HQ: `/hq`
- Classic HQ fallback: `/hq-classic`

No manual database recreation is required. Migration `0006_conversation_ui.sql` is applied automatically and adds conversation flags.
