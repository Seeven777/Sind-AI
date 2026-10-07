# Open-source / gratuito — avaliação v6

## ADOPT — incorporado agora

### edge-tts
Voz neural online gratuita, sem API key. É o backend padrão da v6 e substitui a voz feminina aleatória do Windows como experiência principal.

### Tailscale Serve
Transporte HTTPS privado para o cliente mobile. Mantém o runtime no PC e expõe a interface apenas aos dispositivos autorizados na tailnet.

## ADAPT — preparado

### Chatterbox TTS
Adapter pronto para um endpoint local/OpenAI-compatible. É uma opção open-source mais pesada para voz/voice cloning sem acoplar o modelo ao processo principal do Jarvis.

## REFERENCE — próximas capacidades úteis

### Silero VAD
Voice Activity Detection local. Útil para Jarvis perceber início/fim da fala e permitir conversação mais natural/barge-in.

### faster-whisper
STT local eficiente. Candidato para substituir a dependência do reconhecimento do navegador e tornar voz móvel/desktop mais consistente.

### openWakeWord
Pode dar ao Jarvis wake word contínua. O código é permissivo, mas modelos pré-treinados possuem licença não comercial; não foi instalado automaticamente.

### LiveKit
Boa referência futura para áudio realtime/WebRTC quando o cliente mobile evoluir para conversa contínua de baixa latência.

## Regra

Projetos externos não entram apenas por serem interessantes. Cada integração deve ser classificada em ADOPT / ADAPT / REFERENCE / REJECT, isolada quando pesada, testada e ligada a uma capacidade concreta do Jarvis.
