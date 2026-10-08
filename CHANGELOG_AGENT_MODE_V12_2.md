# Jarvis Agent Mode v12.2 — Interactive Morning Runtime Fix

- Corrige cache antigo do Service Worker que podia manter `companion.js` da v12 enquanto o backend já estava em v12.1.
- Assets críticos agora usam build query `v=12.2` e estratégia network-first/no-cache.
- O briefing manual mostra estado visual de preparação imediatamente antes de sincronizar fontes.
- Sincronização de Gmail, Calendar e Marketing ocorre em paralelo e possui timeout isolado por conector.
- Ação `morning_sequence` deixa de persistir o placeholder textual `Briefing interativo do dia.` no histórico.
- O endpoint de preparação valida o schema da sequência antes de iniciar a coreografia.
- Desktop e mobile usam a mesma correção.
