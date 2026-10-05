# Jarvis Next RC2 — HQ SQLite Thread-Affinity Hotfix

## Sintoma

A UI local retornava erros semelhantes a:

`SQLite objects created in a thread can only be used in that same thread.`

## Causa

`serve_hq()` cria o ProductRuntime (e a conexão SQLite) na thread do event loop,
mas o `ThreadingHTTPServer` executa cada request em uma worker thread. Alguns
endpoints chamavam serviços/repositórios síncronos diretamente da worker.

## Correção

`_State.call_sync()` agenda chamadas síncronas no event loop proprietário usando
`loop.call_soon_threadsafe()`. Endpoints do HQ que tocam runtime, repositórios,
memória, briefing, projetos, skills e health agora usam esse caminho.

A correção preserva `sqlite3` com sua proteção padrão de afinidade de thread; não
usa `check_same_thread=False` como atalho.

## Validação

- teste de regressão `test_hq_thread_affinity.py` executa um request HTTP em uma
  worker e confirma que `HQ.snapshot()` roda na thread proprietária do runtime;
- suíte completa: 63 testes aprovados.

## Instalação

1. Feche o Jarvis com `Stop-Jarvis.cmd`.
2. Extraia o overlay na raiz `C:\Users\AMD\Desktop\Sind-AI`, substituindo arquivos.
3. Rode `Validate-Jarvis-Complete.cmd`.
4. Inicie novamente com `Start-Jarvis.cmd`.
