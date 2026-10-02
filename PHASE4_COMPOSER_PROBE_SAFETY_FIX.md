# Phase 4 — Composer Probe + Safety Fix

## O que o último teste provou

A janela correta do WhatsApp é o `Chrome_WidgetWin_1` hospedado em
`msedgewebview2.exe`. Ela expõe 103 descendants e uma árvore UIA rica.

O probe mostrou:
- RootWebArea (Document, read-only)
- campo de busca (Edit)
- nenhum compositor identificado como Edit/Document

## Correções deste overlay

1. `alpha_zero=true` só é aceito quando um probe UIA real comprova uma árvore útil.
2. compositor ambíguo volta a falhar fechado.
3. `--probe` agora lista controles estruturais da metade inferior da janela:
   - nome
   - automation_id
   - control_type
   - bounds
   - patterns UIA disponíveis
   - indício de compositor

O probe continua somente leitura: não clica, não digita e não envia.

## Instalação

Extraia por cima da raiz do projeto e rode:

```powershell
.\.venv\Scripts\python.exe .\run_phase4_tests.py
```

Depois, abra manualmente `Me (você)` e mantenha a conversa aberta:

```powershell
.\.venv\Scripts\python.exe .\run_phase4_tests.py --probe
```

Envie o JSON gerado. A seção mais importante agora é `"controls"`.
