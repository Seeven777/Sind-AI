# Agent Mode — Presence v2

## Companion
- Home reconstruída como uma presença minimalista: núcleo, composer e menu retrátil.
- Sidebars fixas, cards, quick actions e contextual pop-apps removidos da Home.
- Histórico e todas as áreas do produto permanecem acessíveis pelo drawer superior esquerdo.
- Conversa passa a usar transcript limpo sem bolhas pesadas.
- Indicador de atenção migrou para o botão de menu e para uma fila compacta dentro do drawer.

## Living Core v2
- Shader simplificado e orgânico, sem HUDs/rings decorativos excessivos.
- Estados IDLE/LISTENING/THINKING/RESEARCHING/EXECUTING/VERIFYING/SPEAKING/ATTENTION/ERROR continuam dirigindo movimento e cor.
- Interação de ponteiro e amplitude de voz influenciam o núcleo.

## Voice
- Respostas do Jarvis são faladas automaticamente por padrão.
- Ordem de TTS: ElevenLabs -> Piper -> Web Speech fallback.
- O áudio do backend alimenta o núcleo durante a fala.
- O botão de microfone continua permitindo ditado quando SpeechRecognition está disponível.
- Briefing matinal falado e pedido de atenção por voz preservados.

## Mobile foundation
- Layout responsivo.
- Manifest PWA + service worker adicionados.
- Notificações do navegador opcionais, solicitadas somente por ação do usuário.
- Nenhuma porta de rede externa é aberta automaticamente nesta versão.
