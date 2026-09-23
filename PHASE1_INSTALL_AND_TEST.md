# Personal Autonomy Phase 1 — instalação e teste

Este pacote foi desenhado para ser **aditivo** sobre a versão pública atual do Sind-AI 1.9.

## Arquivos alterados

Substituir:

- `observe/engine.py`
- `swarm/demonstration.py`
- `actions/hub.py`

Adicionar:

- `observe/activity_store.py`
- `observe/context.py`
- `observe/app_registry.py`
- `observe/patterns.py`
- `actions/catalog.d/personal_runtime.json`
- `tests/test_personal_observer.py`
- `run_personal_observer_tests.py`
- `PERSONAL_AUTONOMY_ROADMAP.md`

`observe/__init__.py` pode ser adicionado/substituído; ele contém apenas documentação de pacote.

## Por que não altera `core/agent.py`

A versão atual já instancia `ObservationEngine`, injeta o engine em `ActionHub` e chama `DemonstrationTeacher.handle()` antes do fluxo cognitivo principal. O patch aproveita esses pontos de extensão já existentes.

Isso reduz o risco de regressão no arquivo `core/agent.py` (~3 mil linhas).

## Validar antes de commit

Na raiz do repositório:

```powershell
python .\run_personal_observer_tests.py
python -m compileall observe swarm actions
```

Depois:

```powershell
git status
git diff
git add .
git commit -m "feat: personal context observer foundation"
git push
```

## Sobre a Vercel

O deploy da Vercel valida/distribui o portal web do repositório, mas o observador pessoal é um recurso do **runtime Windows local**. Depois do push, atualize/reabra o Jarvis local pela rotina de atualização já existente para testar a funcionalidade no desktop.

## Teste funcional no chat do Jarvis

Digite exatamente:

```text
ative o aprendizado contínuo
```

Troque entre alguns programas por alguns minutos e teste:

```text
status do observador pessoal
o que estou fazendo agora?
o que eu fiz nos últimos 10 minutos?
resuma minha atividade dos últimos 10 minutos
quais padrões de trabalho você percebeu?
```

Para parar:

```text
desative o aprendizado contínuo
```

A configuração fica persistida em:

```text
~/JarvisData/observe/activity.db
```

Quando ativado uma vez, o observador volta automaticamente nas próximas inicializações até ser desativado.

## Privacidade desta fase

O modo contínuo registra apenas contexto estrutural:

- aplicativo/processo;
- título da janela;
- documento/projeto inferido pelo título;
- mudanças de foco;
- futuros eventos estruturados enviados por bridges.

Ele **não** registra:

- conteúdo digitado;
- clipboard;
- áudio;
- câmera;
- screenshots contínuos.

A demonstração explícita existente mantém o comportamento anterior: texto imprimível é mascarado e convertido em entradas variáveis.
