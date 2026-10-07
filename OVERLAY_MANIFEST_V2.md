# Overlay — AgentMode Presence v2

Copie o conteúdo deste overlay sobre a raiz do repositório `Sind-AI`, preservando a estrutura de pastas.

Principais substituições:

- `src/jarvis/ui/hq_web/companion.html`
- `src/jarvis/ui/hq_web/companion.css`
- `src/jarvis/ui/hq_web/companion.js`
- `src/jarvis/ui/hq_web/jarvis-core.js`
- `src/jarvis/hq/server.py`
- `src/jarvis/voice/base.py`

Novos arquivos:

- `src/jarvis/ui/hq_web/manifest.webmanifest`
- `src/jarvis/ui/hq_web/sw.js`
- `src/jarvis/ui/hq_web/jarvis-icon.svg`
- `Configure-Jarvis-Voice.cmd`
- `Configure-Jarvis-Voice.ps1`
- `docs/VOICE_SETUP_V2.md`
- `CHANGELOG_AGENT_MODE_V2.md`
- `tests/product/test_companion_presence_v2.py`

Depois da substituição, reinicie o Jarvis. Nenhuma nova dependência Python ou NPM é obrigatória.
