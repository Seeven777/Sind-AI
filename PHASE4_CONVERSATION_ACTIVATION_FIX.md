# Phase 4 — Conversation Activation Fix

A captura confirmou que `Me (você)` já é localizado e selecionado com contorno
verde, mas a conversa não abre no painel direito.

## Correção

No WhatsApp WebView2 atual:

```text
SelectionItem.Select()
→ set_focus()
→ Enter
```

`Select()` apenas destaca a linha. O Enter abre a conversa.

Fallbacks mantidos:
- `Invoke()` para builds antigos;
- `double_click_input()` como último recurso;
- nenhuma coordenada fixa.

A lógica de envio não foi alterada.

## Teste

Extraia sobre a raiz do projeto, rode:

```powershell
.\.venv\Scripts\python.exe .\run_phase4_tests.py
```

Reinicie completamente o Jarvis e execute somente:

```text
abra o WhatsApp
selecione a conversa Me (você)
```

O painel direito deve abrir a conversa real antes de avançarmos para digitação.
