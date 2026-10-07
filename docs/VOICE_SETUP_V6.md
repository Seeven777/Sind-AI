# Voz — Presence v6

## Padrão

O Jarvis usa **Edge Neural TTS** como voz gratuita padrão, sem exigir chave de API. O perfil inicial é masculino em português do Brasil:

- voz: `pt-BR-AntonioNeural`
- velocidade: `-6%`
- pitch: `-14Hz`
- processamento de presença/robô leve no cliente WebAudio

Execute `Configure-Jarvis-Voice.cmd` para trocar o backend ou a voz.

## Ordem automática

1. Chatterbox configurado
2. Edge Neural TTS
3. ElevenLabs configurado
4. Piper configurado
5. Windows SAPI
6. Web Speech no navegador, quando aplicável

## Chatterbox

Há um adaptador para servidor Chatterbox/OpenAI-compatible. O modelo pesado fica isolado do ambiente principal do Jarvis. Configure `JARVIS_CHATTERBOX_URL` ou use `Configure-Jarvis-Voice.cmd`.

## Diagnóstico

Execute `Test-Jarvis-Voice.cmd`.

O teste mostra o backend ativo e tenta gerar um arquivo de áudio real. Se o backend reportado for `windows-sapi`, a voz neural anterior não está disponível e o sistema está em fallback.
