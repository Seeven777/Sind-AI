# Agent Mode Presence v7

## Visual / UX

- Refinamento visual global das superfícies desktop.
- Office com materiais, iluminação, profundidade, painéis e HUD refinados.
- Companion/Core com presença mais controlada e acabamento consistente.
- Mobile redesenhado para safe areas, teclado virtual, toque e navegação compacta.
- Design tokens, vidro, linhas, sombras, estados e microinterações unificados.
- Reduced-motion respeitado no mobile.

## Jarvis Anywhere

- Novo acesso público HTTPS usando Tailscale Funnel.
- Nenhum app é necessário no dispositivo cliente.
- Mesmo runtime, memória, agentes, modelos e missões do PC.
- Links separados para mobile e desktop.
- Configuração persistente em background.
- Status e desligamento dedicados.

## Segurança remota

- Corrigida confiança indevida em `client_address` quando há reverse proxy.
- `Host`, `CF-Connecting-IP` e `X-Forwarded-For` agora participam da decisão local/remota.
- Sessão remota ganha `Secure` sob HTTPS e expiração explícita.
- Token da URL é removido após estabelecer a sessão.
- Launchers de background iniciam o runtime com proteção mobile ativa.

## Validação

- Testes v7 cobrem Funnel, proxy/auth, cookies HTTPS, startup remoto e contratos visuais.
