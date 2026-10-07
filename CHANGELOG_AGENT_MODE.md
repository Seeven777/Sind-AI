# Agent Mode — atualização acumulada

## Implementado

- Autonomous Curiosity Loop persistente.
- Pesquisa espontânea sobre qualquer assunto.
- Memória de descobertas e deduplicação de propostas.
- Autoavaliação e propostas de melhoria com aprovação humana.
- Fila de atenção com níveis `ambient`, `important` e `critical`.
- Briefing diário com clima, notícias, responsabilidades e evolução do Jarvis.
- Solicitação de atenção por UI e voz.
- Cumprimento matinal curto.
- Novo Jarvis Core WebGL2 interativo com fallback Canvas 2D.
- Home redesenhada para funcionar como espaço de presença, não painel de cards.
- Contextual Surfaces para briefing, descobertas e melhorias.
- Agent Office com núcleo de partículas, data paths, handoffs e estados visuais reais.
- `ASSISTING` visual separado de `EXECUTING` real.
- Scripts para iniciar/remover Jarvis no logon do Windows.
- Migração SQLite `0008_autonomous_life.sql`.

## Validação

- suíte Python: 93 testes aprovados;
- release self-test: todos os gates aprovados;
- JavaScript alterado validado com `node --check`;
- shader do Jarvis Core compilado e renderizado em Chromium/WebGL2 sem erro.
