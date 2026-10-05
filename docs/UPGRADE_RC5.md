# Upgrade to Jarvis Next RC5

1. Stop the current Jarvis instance.
2. Extract the RC5 Full package over the existing project directory, preserving `.git`, `.venv` and the user's data directory.
3. Reinstall the editable package.
4. Run the full validation script.
5. Start the application.

Expected validation result:

```text
87 passed
```

Primary URLs:

- Companion: `http://127.0.0.1:4760/`
- HQ: `http://127.0.0.1:4760/hq`
- Mission Control: `http://127.0.0.1:4760/mission-control`
- Agents: `http://127.0.0.1:4760/agents`
- Memory: `http://127.0.0.1:4760/memory`
- System: `http://127.0.0.1:4760/system`

The RC5 spatial HQ no longer depends on a browser-side Three.js import, so an unavailable CDN does not blank the office scene.
