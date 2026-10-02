# Auditoria de limpeza e manutenção do Sind-AI

## Não remover automaticamente
- `%USERPROFILE%/JarvisData`: memória, conversas, experiência, projetos e bancos persistentes.
- `.venv` e `.venv-openjarvis`: necessários para a instalação atual; só recriar se houver motivo.
- `runtime/phase4`: execução física/verificação, especialmente WhatsApp/UI Automation.
- `core/openjarvis_bridge.py`, `run_integrated_jarvis.py` e configs do OpenJarvis.
- bancos `.db/.sqlite` fora do Git se contiverem estado do usuário.

## Limpeza segura imediata
O utilitário `scripts/cleanup_project.py` pode remover apenas caches não rastreados:
- `__pycache__`;
- `.pytest_cache`;
- `.ruff_cache`;
- `.mypy_cache`;
- `.pyc/.pyo` não rastreados;
- logs não rastreados.

Ele opera em modo relatório por padrão e ignora arquivos rastreados pelo Git.

## Itens rastreados que merecem limpeza em commit separado
A auditoria do `main` mostrou artefatos gerados rastreados, incluindo `__pycache__/*.pyc`.
Recomendação: removê-los do índice do Git em um commit de higiene, sem misturar com mudanças funcionais.

## Arquivos grandes
O repositório auditado tinha ~106 MB rastreados. O maior arquivo era:
`desktop/src-tauri/binaries/ollama-aarch64-apple-darwin` (~73,5 MB).

Para um fork exclusivamente Windows, esse binário Apple Silicon não é necessário em runtime. Porém ele faz parte da camada upstream do OpenJarvis e não é removido por este overlay para não quebrar builds/release multiplataforma.

Também há assets de demonstração e ícones de distribuição que podem ser movidos para assets de release/documentação se o objetivo for reduzir clone/deploy.

## Arquitetura
`core/agent.py` continua concentrando muitas responsabilidades. Próxima refatoração recomendada:
1. composition root separado;
2. registry declarativo de ferramentas (`name`, schema, risk, execute, verify`);
3. event bus tipado runtime -> UI;
4. adaptadores para ferramentas legadas;
5. separar fork/personalizações Sind-AI do upstream OpenJarvis.

Essa refatoração deve ser feita com testes, sem reescrever executores Phase 4 já validados.

## Vercel
O desktop/local runtime não deve ser enviado à Vercel. O overlay mantém apenas o portal estático no deploy via `.vercelignore`, `framework: null`, build customizado e `vercel_dist`.
