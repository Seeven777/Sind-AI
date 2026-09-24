# Phase 4 — Search Result Selection Fix

O raw probe confirmou que o WhatsApp WebView2 concatena o contato com horário/data e preview dentro de DataItem.

Correção:
- sem fuzzy matching;
- aceita somente contato exato seguido por metadado típico (hora/data/dia);
- metadado estendido só vale dentro de DataGrid “Resultados da pesquisa.”;
- prioriza DataItem largo com SelectionItem;
- colapsa nós duplicados do WebView2;
- ativa o resultado com SelectionItem + click;
- mantém fail-closed para resultados realmente ambíguos.

Teste primeiro apenas:

```text
abra o WhatsApp
selecione a conversa Me (você)
```

Não envie mensagem ainda.
