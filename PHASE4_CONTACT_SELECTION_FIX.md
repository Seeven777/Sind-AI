# Phase 4 — Contact Selection Fix

O WhatsApp já abre e o Jarvis já consegue escrever `Me (você)` na busca.
O bloqueio atual é identificar/clicar o resultado na árvore WebView2.

Esta correção:
- deixa de exigir `ListItem`/`DataItem`;
- aceita rótulos exatos como Text/Custom/Group/Pane;
- sobe do rótulo para o ancestral clicável;
- restringe o alvo à área de resultados;
- usa click_input se Invoke existir mas falhar;
- mantém correspondência exata do contato;
- corrige 5 regressões do parser de intenção.

## Instalação

Feche o Jarvis e extraia o ZIP sobre a raiz.

```powershell
.\.venv\Scripts\python.exe .\run_phase4_tests.py
```

Depois teste:

```text
abra o WhatsApp
selecione a conversa Me (você)
```

Só depois:

```text
escreva "teste contato" no campo de mensagem, mas não envie
```
