# Changelog JARVIS

## 2026-10-01 — Habitat cinematográfico

- Adicionado orb procedural em Canvas 2D com partículas, membranas, órbitas, profundidade e estados reais.
- Adicionados perfis visuais `low`, `medium` e `high`, com seleção automática conservadora.
- A navegação lateral passou a drawer sob demanda.
- O idle foi reduzido a orb, status, hora, telemetria mínima e comando.
- A conversa passou a ocupar uma superfície contextual lateral.
- O bridge visual agora distingue listening, thinking, planning, executing, observing, verifying e speaking.
- Sucesso e erro produzem feedback visual temporário sem inventar execução.
- Mantidos os modais, ferramentas, histórico, projetos e centro de controle existentes.
- Adicionada documentação de arquitetura, UI, ferramentas, memória e testes.
- Adicionada conversa por voz local com captura até silêncio, Faster-Whisper e síntese nativa do Windows.
- O orb agora responde à amplitude do microfone e ao estado de fala do JARVIS.
- Adicionadas interações por cursor, arrastar, roda do mouse e duplo clique para restaurar.

## 2026-10-02 — Voz neural e contexto vivo

- Configurada a voz ElevenLabs `2CECaLAGTS5NRGxgbcxr` como provider preferencial no backend, com fallback local.
- Adicionado gerador TTS isolado; a chave permanece somente no ambiente do processo.
- Adicionado widget meteorológico animado com dados atuais e previsão de cinco dias.
- Consultas comuns de clima agora usam Open-Meteo diretamente, reduzindo latência e evitando uma chamada desnecessária ao LLM.
- Adicionado cache curto de saúde e reuso de conexão no bridge OpenJarvis.
- O orb ganhou arcos energéticos, envelope de fala e transições de contexto mais orgânicas.
