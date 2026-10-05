# Jarvis RC5 Fix

Corrige os dois problemas observados na validação do RC5:

- Hermes: força UTF-8 no subprocesso para preservar prompts/respostas com acentuação no Windows.
- PDF: declara `reportlab` e `pypdf` como dependências de runtime, evitando `No module named reportlab`.
- Launcher: captura stdout/stderr, salva logs e oferece 60s de grace period para diagnósticos de inicialização.

Após aplicar, execute `pip install -e ".[dev]"` novamente e `Validate-Jarvis-Complete.cmd`.
