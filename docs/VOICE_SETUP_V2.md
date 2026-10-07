# Jarvis Voice v2

A Home usa voz em duas camadas:

1. **TTS do Jarvis**: ElevenLabs quando configurado; Piper local como alternativa.
2. **Fallback automático**: Web Speech do navegador/Windows quando nenhum backend está configurado.

Isso significa que a interface continua falando sem configuração obrigatória. Para a voz premium desejada, execute `Configure-Jarvis-Voice.cmd`, informe a API Key e o Voice ID da ElevenLabs e reinicie o Jarvis.

Variáveis suportadas:

- `JARVIS_ELEVENLABS_API_KEY`
- `JARVIS_ELEVENLABS_VOICE_ID`
- `JARVIS_ELEVENLABS_MODEL` (opcional, padrão `eleven_multilingual_v2`)
- `JARVIS_TTS_PROVIDER=elevenlabs|piper|auto`
- `JARVIS_PIPER`
- `JARVIS_PIPER_MODEL`

As chaves nunca são enviadas para a UI do Companion. A síntese ocorre no backend local e a página recebe somente o áudio.
