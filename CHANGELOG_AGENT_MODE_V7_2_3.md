# Agent Mode v7.2.3 — Anywhere DNS propagation hotfix

- Corrige falso negativo logo após a criação de Quick Tunnels no Windows.
- A validação agora consulta DNS público 1.1.1.1 e usa curl com DNS-over-HTTPS como fallback.
- Mantém o túnel vivo por até 240 segundos enquanto o hostname `trycloudflare.com` propaga.
- Distingue propagação DNS, 502 de origem e falhas de autenticação.
- Ignora o aviso informativo de certificate pool do cloudflared quando a origem é HTTP.
