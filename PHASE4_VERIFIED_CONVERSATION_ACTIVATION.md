# Phase 4 — Verified Conversation Activation

A captura mostrou que o patch anterior limpou a pesquisa, mas não abriu a conversa.

Correção:
- prefere o DataItem interno `Me (você) 07:11` com SelectionItem;
- clique físico nesse alvo;
- Enter somente se o foco de teclado for realmente confirmado;
- double click como fallback;
- Invoke para compatibilidade;
- cada tentativa só é aceita quando `Me (você)` aparece no cabeçalho do painel direito;
- nenhuma mensagem é digitada ou enviada.

Teste:

```powershell
.\.venv\Scripts\python.exe .\run_phase4_tests.py
```

Depois reinicie o Jarvis e execute apenas:

```text
abra o WhatsApp
selecione a conversa Me (você)
```
