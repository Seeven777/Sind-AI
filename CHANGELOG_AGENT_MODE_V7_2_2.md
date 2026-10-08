# Agent Mode v7.2.2 — Anywhere origin fix

- Cloudflare Quick Tunnel agora usa `http://127.0.0.1:4760` explicitamente, evitando resolução de `localhost` para `::1` enquanto o servidor Jarvis está em IPv4.
- `/api/*?token=` não faz mais redirecionamento de sessão; APIs autenticadas retornam diretamente, tornando a prova pública determinística.
- A validação pública distingue 502/503/504 (origem inalcançável) de 401/403/404 (origem alcançada, problema de autenticação/rota).
- Diagnóstico do Anywhere mostra a origem IPv4 usada pelo `cloudflared`.
- Logs de erro agora priorizam linhas relacionadas a origem/conexão em vez de apenas o precheck saudável da Cloudflare.
