# Jarvis Anywhere v7.1

`Enable-Jarvis-Anywhere.cmd` now creates a browser-only public bridge and validates it before showing the link.

Order:
1. Cloudflare Quick Tunnel (default, no app on visitor device)
2. Tailscale Funnel (fallback)

The local Jarvis remains the origin: the PC must stay powered on and online.

## Important

A Cloudflare Quick Tunnel URL is temporary and can change when the tunnel restarts. `Jarvis-Anywhere-Status.cmd` shows the current URL. Windows startup will recreate the bridge automatically when Jarvis Anywhere had previously been enabled.

The query token grants owner-level access to the current Jarvis web surface. Do not publish it openly. A restricted guest/pairing layer should be used before intentionally sharing Jarvis with third parties.
