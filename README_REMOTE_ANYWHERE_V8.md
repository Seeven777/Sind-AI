# Jarvis Anywhere v8

A v8 simplifica o acesso remoto. O Jarvis continua rodando no PC, mas o acesso público usa **ngrok** em vez da cadeia Tailscale/Cloudflare Quick Tunnel.

## Primeira vez

1. Execute `Jarvis-Anywhere.cmd`.
2. Se necessário, o script instala o ngrok pelo WinGet/Microsoft Store.
3. A página oficial do ngrok será aberta. Crie uma conta gratuita, copie seu authtoken e cole na janela.
4. O script cria e valida o endereço público antes de mostrá-lo.

Depois disso, basta o PC estar ligado. O serviço em segundo plano recria o acesso automaticamente quando o Jarvis inicia.

O celular ou computador visitante **não precisa instalar nada**. Basta abrir o link HTTPS no navegador.

O token do Jarvis continua sendo trocado por um cookie HttpOnly e removido da URL após a primeira navegação.
