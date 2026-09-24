# Phase 4 — UIA Accessibility Window Fix

## Causa encontrada

No WhatsApp Microsoft Store da máquina de teste, a janela está fisicamente na tela,
mas Win32/pywinauto reporta:

- `WhatsApp.Root.exe / WinUIDesktopWin32WindowClass`: `visible=false`
- `msedgewebview2.exe / Chrome_WidgetWin_1`: `visible=false`, `alpha_zero=true`

Esses flags não podem ser usados como verdade absoluta em WinUI 3 + WebView2.

## Correção

O Jarvis agora:

1. enumera a árvore de processos WhatsApp.Root/WebView2;
2. mantém candidatos de tamanho real mesmo quando `visible=false`;
3. tenta cada HWND candidato em modo UIA somente leitura;
4. mede quantidade de descendants, campos, botões e nomes reconhecíveis;
5. escolhe a árvore de acessibilidade mais rica;
6. usa foco nativo por HWND como fallback;
7. não descarta automaticamente `alpha_zero=true`;
8. aceita campos WebView2 com retângulo real mesmo se o ancestral reportar invisibilidade.

## Instalação

Extraia este overlay na raiz do projeto, substituindo os arquivos existentes.

Depois:

```powershell
.\.venv\Scripts\python.exe .\run_phase4_tests.py
```

Com o WhatsApp aberto na conversa `Me (você)`:

```powershell
.\.venv\Scripts\python.exe .\run_phase4_tests.py --probe
```

O resultado esperado agora é `ok: true`, um `chosen` com `uia_ok: true` e
`fields` contendo a busca e/ou o compositor.

Não envie mensagens ainda. Primeiro valide apenas leitura do campo e digitação sem envio.
