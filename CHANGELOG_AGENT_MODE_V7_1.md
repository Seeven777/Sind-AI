# Jarvis Agent Mode v7.1 — Anywhere Reliability Hotfix

- Jarvis Anywhere now prefers a Cloudflare Quick Tunnel for browser-only public access.
- Tailscale Funnel remains available as automatic fallback.
- The launcher validates the public URL against `/api/ping` before declaring success.
- `cloudflared` is downloaded automatically from Cloudflare's official GitHub release when absent.
- Public bridge runs in the background and its PID/provider are persisted.
- Windows startup restores Jarvis Anywhere automatically when it was previously enabled.
- Status and disable scripts understand both Cloudflare and Tailscale providers.
- Console scripts use UTF-8 to avoid mojibake in Portuguese output.

Quick Tunnel URLs are intentionally temporary and can change after a tunnel restart. A stable public hostname will require a named tunnel/domain in a later step.
