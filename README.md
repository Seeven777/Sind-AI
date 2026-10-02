# Jarvis Next

Novo núcleo do Jarvis, reconstruído do zero.

## Phase 0 — Foundation

Esta fase não contém IA, Ollama, voz, UI ou automação.

Ela implementa somente:

- configuração;
- SQLite WAL;
- migrations;
- Event Bus;
- persistência de eventos;
- tasks;
- checkpoints;
- lifecycle;
- detecção de shutdown incorreto;
- recovery;
- single-instance lock;
- health;
- testes.

## Desenvolvimento

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest
python -m jarvis --once
```

Para usar um diretório de dados de teste:

```powershell
$env:JARVIS_DATA_DIR="$PWD\.jarvis-data"
python -m jarvis --once
```
