# Computer Runtime V5 — Foreground Ownership

## Causa confirmada pelo V4

O UIA do WhatsApp reportou o contato em coordenadas corretas, mas
`ElementFromPoint` encontrou Explorer e PowerShell nessas mesmas coordenadas.

Isso prova que a árvore do WhatsApp estava sendo inspecionada em background.

## Correção V5

- identifica separadamente:
  - renderer WebView2 (`Chrome_WidgetWin_1`) para leitura UIA;
  - shell WinUI (`WhatsApp.Root.exe / WinUIDesktopWin32WindowClass`) para z-order;
- foreground é aplicado ao shell real;
- usa AttachThreadInput + SetForegroundWindow;
- usa TOPMOST apenas transitoriamente e remove imediatamente;
- registra `focus_trace`;
- exige evidência de que o foreground pertence ao WhatsApp antes de qualquer hit-test;
- mantém o hit-test V4: nenhum clique ocorre se o pixel não pertencer ao contato.

## Executar

Feche o Jarvis, extraia na raiz e execute:

```powershell
.\.venv\Scripts\python.exe .\apply_computer_runtime_v5.py
.\.venv\Scripts\python.exe .\run_computer_v5_tests.py
.\.venv\Scripts\python.exe .\computer_v5_benchmark.py --contact "Me (você)"
```

Não teste rascunho ou envio antes do benchmark de abertura retornar `ok: true`.
