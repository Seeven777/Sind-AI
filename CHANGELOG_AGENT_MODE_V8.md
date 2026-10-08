# Agent Mode v8 — Anywhere simplificado

- Remove Cloudflare Quick Tunnel como caminho padrão.
- Remove dependência de Tailscale no dispositivo visitante.
- Usa ngrok como ponte pública estável e testável.
- Instalação assistida pelo WinGet.
- Authtoken configurado uma única vez.
- Link só é exibido após `/api/ping` responder pelo endereço público.
- Auto-recovery no boot reutiliza `Enable-Jarvis-Anywhere.ps1 -Auto`.
- Mantém token remoto + sessão HttpOnly do Jarvis.
