# Computer Runtime V5.1 — Foreground Hotfix

O V5 tinha um bug de inicialização: `last_focus_trace` e `shell_metadata`
eram usados antes de serem inicializados no construtor.

V5.1:
- inicializa todo o estado diagnóstico;
- torna `_focus_whatsapp()` defensivo;
- `open()` agora promove a janela raiz do WhatsApp para foreground desde o começo;
- preserva todo o V5: shell WinUI, hit-test, SendInput e verificação de cabeçalho.

Execute:

```powershell
.\.venv\Scripts\python.exe .\apply_computer_runtime_v51.py
.\.venv\Scripts\python.exe .\run_computer_v51_tests.py
.\.venv\Scripts\python.exe .\computer_v51_benchmark.py --contact "Me (você)"
```

Não rode draft/envio antes de `ok: true`.
