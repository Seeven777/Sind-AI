# JARVIS integrado com OpenJarvis

Esta pasta reúne duas camadas que permanecem isoladas por desenho:

- o JARVIS/Sind-AI existente, com interface PySide6, automações, memória e ferramentas;
- o OpenJarvis oficial, usado como núcleo conversacional local por API em `127.0.0.1:8000`.

## Iniciar

Clique duas vezes em `Iniciar-Jarvis-Integrado.cmd`.

O inicializador:

1. sobe o servidor OpenJarvis local sem abrir uma janela de terminal extra;
2. aguarda o endpoint de saúde;
3. abre a interface JARVIS existente;
4. encerra o servidor que iniciou quando a interface for fechada.

Se já houver um servidor OpenJarvis na porta 8000, ele será reutilizado e não será encerrado.

## Componentes instalados

- Python 3.13 lado a lado com o Python 3.14 existente;
- `uv` 0.12.21;
- Rustup/Cargo;
- Microsoft Visual C++ Build Tools 2022;
- ambiente `.venv-openjarvis` com OpenJarvis e o módulo `openjarvis_rust`;
- modelo Ollama `qwen3.5:2b`.

O ambiente antigo `.venv` não foi substituído.

## Configuração

A configuração oficial fica em `%USERPROFILE%\.openjarvis\config.toml`.
A ponte do JARVIS fica em `data/config.json`, nas chaves `openjarvis_*`.

Se o backend oficial estiver indisponível, a conversa volta automaticamente ao roteador Ollama antigo. As ações e automações continuam sendo executadas pelo runtime antigo, preservando as funcionalidades específicas já construídas.

## Atualização segura

Não use `git pull` às cegas nesta pasta: ela também contém personalizações locais. Antes de atualizar, confira `git status`, preserve os arquivos locais e valide a atualização em um branch separado. Depois da atualização oficial, recrie o ambiente com o Developer PowerShell do Visual Studio:

```powershell
$env:UV_PROJECT_ENVIRONMENT = '.venv-openjarvis'
uv sync --python 3.13 --extra desktop --group desktop-native
```

## Validação rápida

```powershell
.\.venv\Scripts\python.exe .\run_integrated_jarvis.py --check
.\.venv-openjarvis\Scripts\python.exe -c "import openjarvis_rust; print('OK')"
.\.venv-openjarvis\Scripts\jarvis.exe ask --no-stream --json "Responda somente OK"
.\.venv\Scripts\python.exe .\foundation_regression_test.py
.\.venv\Scripts\python.exe .\cognitive_test.py
```
