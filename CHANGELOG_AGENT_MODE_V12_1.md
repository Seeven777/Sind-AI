# Agent Mode v12.1 — Interactive Briefing Hotfix

- Corrige o comando natural "Jarvis, faça meu briefing completo do dia" para acionar a sequência visual, em vez de cair no LLM genérico.
- Replays/briefings manuais agora usam `/api/morning/prepare`, sincronizando conectores e atualizando clima, notícias e tarefas antes da animação.
- Desktop e mobile interceptam a ação `morning_sequence` antes de renderizar prosa.
- O streaming não envia texto transitório para comandos de briefing interativo.
- Adiciona testes de regressão para as frases reais usadas pelo usuário.
