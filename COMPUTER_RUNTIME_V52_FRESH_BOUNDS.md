# Computer Runtime V5.2 — Fresh Bounds

## Causa confirmada

V5.1 provou que o WhatsApp realmente fica em foreground.

O `ElementFromPoint` retorna apenas:

```text
Pane automation_id=WebView
→ Window WhatsApp
```

e não os DataItems internos do DOM.

Isso é comportamento do provider UIA do WebView2, não erro de coordenadas.

## Correção

- `_attach()` volta a ser somente leitura e não altera foreground;
- antes de uma ação física:
  1. traz a janela raiz do WhatsApp para frente;
  2. readquire a árvore raw;
  3. encontra novamente o resultado único;
  4. lê bounds NOVOS;
  5. aceita hit-test genérico `WebView → WhatsApp` como prova de ownership;
  6. somente então injeta o clique;
  7. verifica o cabeçalho;
- fallback 2: busca raw única + `Down` + `Enter`;
- fallback 3: nova readquisição + double-click;
- não reutiliza wrappers/bounds obtidos antes de focus;
- observação não rouba foco;
- benchmark continua sem enviar mensagens.

## Executar

```powershell
.\.venv\Scripts\python.exe .\apply_computer_runtime_v52.py
.\.venv\Scripts\python.exe .\run_computer_v52_tests.py
.\.venv\Scripts\python.exe .\computer_v52_benchmark.py --contact "Me (você)"
```

Não execute draft/envio antes de `ok: true`.
