# Arquitetura da interface

## Composição

- `ui/web/index.html`: estrutura do habitat e superfícies contextuais.
- `ui/web/styles.css`: estilos legados preservados para controles e modais.
- `ui/web/habitat.css`: camada visual cinematográfica carregada por último.
- `ui/web/orb.js`: renderizador procedural Canvas 2D.
- `ui/web/app.js`: conversa, widgets existentes e ligação com `QWebChannel`.
- `ui/habitat.py`: tradução de eventos do agente para estados visuais.

## Estados do orb

`idle`, `listening`, `thinking`, `planning`, `executing`, `observing`, `verifying`, `speaking`, `success` e `error` alteram energia, velocidade, cor, pulso e dispersão.

O orb usa núcleo radial, onze membranas com frequências não coincidentes, três órbitas inclinadas e partículas ordenadas por profundidade. A qualidade padrão é escolhida pela quantidade de threads; o usuário pode definir `jarvis-visual-quality` como `low`, `medium` ou `high` no armazenamento local.

## Interação e conversa

- Arrastar gira a dinâmica do campo energético.
- A roda do mouse aproxima ou afasta; duplo clique restaura a visão.
- Movimento do cursor cria parallax orgânico.
- O botão de voz inicia captura local pelo processo `scripts/jarvis_voice_input.py`.
- A amplitude real é enviada ao Canvas durante `LISTENING`.
- Faster-Whisper local transcreve em português e entrega o texto ao mesmo fluxo do agente.
- `QTextToSpeech` usa a voz instalada no Windows para falar a resposta; o orb assume `SPEAKING` durante a reprodução.

O processo de voz separado evita bloquear a thread do Qt ou carregar o modelo Whisper permanentemente no processo visual.

Quando `ELEVENLABS_API_KEY` estiver disponível, as respostas usam a voz neural `2CECaLAGTS5NRGxgbcxr` pelo backend. A chave nunca atravessa o `QWebChannel` nem entra no JavaScript. Sem chave, `QTextToSpeech` permanece como fallback local.

## Widgets contextuais

Widgets recebem dados estruturados em `metadata.widget`, não tentam extrair fatos do texto final. A primeira implementação é o clima: uma consulta comum usa o fast path Open-Meteo já existente, evita uma rodada de LLM e abre uma superfície HUD com condições atuais e cinco dias. O widget se fecha sozinho depois de 18 segundos.

Canvas 2D foi escolhido para manter bom desempenho na Radeon integrada. O DPR é limitado e a quantidade de partículas cai no modo `low`. `prefers-reduced-motion` reduz o movimento.

## Comportamento contextual

- Idle: orb, status, atividade mínima, hora e composer.
- Conversa: orb se desloca e reduz; mensagens surgem à direita.
- Execução: o estado real recebido do backend aumenta energia e velocidade.
- Sucesso/erro: feedback curto; o orb retorna ao idle automaticamente.
- Histórico e recursos: drawer esquerdo somente sob demanda.
- Contexto técnico: painel direito somente sob demanda.

Não há vídeo pré-renderizado, asset copiado ou animação que simule execução.
