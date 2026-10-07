# Agent Mode Presence v6

## Voz

- Edge Neural TTS passa a ser a voz gratuita padrão, sem API key.
- Perfil inicial masculino pt-BR (`pt-BR-AntonioNeural`) com rate/pitch calibrados.
- Processamento WebAudio discreto acrescenta presença sintética sem distorção pesada.
- Chatterbox/OpenAI-compatible preparado como backend local opcional.
- ElevenLabs permanece opcional; Piper e Windows SAPI continuam como fallbacks.
- `Configure-Jarvis-Voice.cmd` foi refeito para escolher o backend.
- `Test-Jarvis-Voice.cmd` agora testa a síntese ativa em vez de assumir SAPI.

## Mobile

- Nova superfície `/mobile`, desenhada especificamente para telefone.
- Mesmo runtime, memória, conversas, atenção, missões e voz do desktop.
- Entrada por voz quando o navegador permite.
- PWA em contexto HTTPS.
- `Enable-Jarvis-Mobile-Secure.cmd` adiciona acesso HTTPS privado via Tailscale Serve.
- Acesso LAN existente continua com token e firewall de rede privada.

## Pesquisa pública

- Edge TTS adotado.
- Tailscale Serve adotado para transporte mobile seguro.
- Chatterbox adaptado como opção futura/local.
- Silero VAD, faster-whisper, openWakeWord e LiveKit classificados como próximas referências de voz/realtime.

## Qualidade

- Testes v6 adicionados para voz, mobile, rota, manifest, Tailscale e processamento de áudio.
- Setup base inclui o extra `voice`.
