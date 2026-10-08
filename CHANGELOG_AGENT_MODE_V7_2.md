# Agent Mode Presence v7.2 — Anywhere reliability hotfix

- Remove Tailscale Funnel as an automatic public fallback.
- A `.ts.net` link is no longer presented as success when Cloudflare failed.
- Public access now requires a working Cloudflare Quick Tunnel to the local Jarvis origin.
- Origin is validated before and after tunnel creation.
- Cloudflared retries with automatic transport and HTTP/2 transport.
- `Jarvis-Anywhere-Status` performs a live health check instead of trusting the stored file.
- Added `Repair-Jarvis-Anywhere.cmd` and `Diagnose-Jarvis-Anywhere.cmd`.
- Legacy Tailscale Funnel state is reset automatically so stale links are not reused.
