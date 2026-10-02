# JARVIS NEXT — PHASE 0 FOUNDATION
## Plano técnico executável
**Versão:** 1.0  
**Objetivo:** construir uma fundação pequena, testável e durável antes de adicionar qualquer IA.

---

# 1. Objetivo da Phase 0

A Phase 0 não terá:

- LLM;
- Ollama;
- voz;
- interface;
- agentes;
- browser;
- WhatsApp;
- connectors;
- automação Windows;
- HQ;
- Model Mesh real.

Ela deve provar uma coisa:

> **O Jarvis possui um núcleo confiável antes de possuir inteligência.**

Ao final da Phase 0 teremos um serviço local capaz de:

1. iniciar;
2. carregar configuração;
3. abrir e validar seu banco;
4. publicar eventos;
5. registrar eventos;
6. criar tasks;
7. salvar checkpoints;
8. recuperar tasks interrompidas;
9. detectar shutdown incorreto;
10. expor health interno;
11. fechar corretamente;
12. ser testado automaticamente.

---

# 2. Regras da Phase 0

## Regra 1 — zero dependência opcional no bootstrap

O Core deve iniciar mesmo que módulos futuros não existam.

## Regra 2 — banco fora do repositório

Código pode ser apagado e reinstalado sem apagar dados.

## Regra 3 — migrations obrigatórias

Nenhuma mudança de schema ocorre “na mão”.

## Regra 4 — todo estado importante é persistido

Não depender de variáveis em memória para continuidade.

## Regra 5 — eventos são contratos

A aplicação não comunica estados importantes por prints soltos.

## Regra 6 — testes antes de features

Phase 1 só começa quando Phase 0 estiver verde.

---

# 3. Plataforma inicial

## Sistema operacional

Windows 11 será a plataforma primária.

Outros sistemas não fazem parte da primeira versão.

## Linguagem

Python.

Escolher uma versão estável e compatível com PySide6 antes da instalação final.  
A versão deve ser fixada no projeto após validação do ambiente.

## Gerenciamento de ambiente

Usar apenas um ambiente virtual:

```text
.venv
```

Nada de múltiplos ambientes paralelos na primeira fase.

## Banco

SQLite com WAL.

## Testes

pytest.

## Configuração

TOML + variáveis de ambiente.

## Logging

logging estruturado em JSONL.

---

# 4. Layout físico

## Repositório

```text
C:\Users\AMD\Desktop\Sind-AI
```

## Dados persistentes

Padrão:

```text
%LOCALAPPDATA%\JarvisNext
```

Estrutura:

```text
JarvisNext/
├── data/
│   └── jarvis.db
├── logs/
│   ├── jarvis.jsonl
│   └── crash.jsonl
├── runtime/
│   ├── instance.lock
│   └── last_shutdown.json
└── config/
    └── config.toml
```

Pode ser sobrescrito por:

```text
JARVIS_DATA_DIR
```

O repositório nunca armazena:

- banco real;
- logs reais;
- secrets;
- caches;
- arquivos de runtime.

---

# 5. Estrutura do repositório na Phase 0

```text
Sind-AI/
│
├── .git/
├── .gitignore
├── README.md
├── pyproject.toml
├── pytest.ini
│
├── docs/
│   ├── JARVIS_MASTER_SPEC_v1.0.md
│   └── PHASE0_FOUNDATION_PLAN.md
│
├── src/
│   └── jarvis/
│       ├── __init__.py
│       ├── __main__.py
│       │
│       ├── app/
│       │   ├── __init__.py
│       │   ├── bootstrap.py
│       │   ├── lifecycle.py
│       │   └── health.py
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   └── models.py
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── events.py
│       │   ├── event_bus.py
│       │   └── errors.py
│       │
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── database.py
│       │   ├── migrations.py
│       │   └── repositories/
│       │       ├── __init__.py
│       │       ├── events.py
│       │       ├── tasks.py
│       │       └── checkpoints.py
│       │
│       └── tasks/
│           ├── __init__.py
│           ├── models.py
│           ├── service.py
│           └── recovery.py
│
├── migrations/
│   └── 0001_foundation.sql
│
├── tests/
│   ├── unit/
│   │   ├── test_event_bus.py
│   │   ├── test_config.py
│   │   └── test_task_state.py
│   │
│   ├── integration/
│   │   ├── test_database.py
│   │   ├── test_event_persistence.py
│   │   └── test_task_checkpoints.py
│   │
│   ├── recovery/
│   │   ├── test_unclean_shutdown.py
│   │   └── test_resume_interrupted_task.py
│   │
│   └── acceptance/
│       └── test_phase0_acceptance.py
│
└── scripts/
    ├── dev_run.ps1
    ├── run_tests.ps1
    └── reset_test_data.ps1
```

---

# 6. pyproject.toml

A Phase 0 deve manter dependências mínimas.

Runtime ideal:

```text
nenhuma ou quase nenhuma dependência externa
```

Dependências de desenvolvimento:

```text
pytest
pytest-asyncio
```

Se decidirmos usar validação estruturada externa, ela só entra se reduzir complexidade real.

Não adicionar:

- FastAPI;
- SQLAlchemy;
- Redis;
- Celery;
- Temporal;
- LangChain;
- LangGraph;
- LiteLLM;
- PySide6;
- Playwright;

na Phase 0.

---

# 7. Configuração

Arquivo:

```text
%LOCALAPPDATA%\JarvisNext\config\config.toml
```

Exemplo:

```toml
[system]
name = "Jarvis"
environment = "development"

[storage]
database = "data/jarvis.db"

[logging]
level = "INFO"
file = "logs/jarvis.jsonl"

[runtime]
resume_interrupted_tasks = true
single_instance = true
```

Prioridade:

```text
defaults
↓
config.toml
↓
environment variables
↓
CLI arguments
```

Configuração inválida deve:

1. registrar erro claro;
2. usar defaults quando seguro;
3. impedir boot apenas quando continuar geraria corrupção.

---

# 8. Banco de dados

Phase 0 usará um único SQLite físico:

```text
jarvis.db
```

Com domínios separados por tabelas.

## 8.1 PRAGMAs

No bootstrap:

```sql
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
PRAGMA synchronous=NORMAL;
PRAGMA busy_timeout=5000;
```

---

# 9. Schema inicial

## 9.1 schema_migrations

```sql
CREATE TABLE schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TEXT NOT NULL
);
```

## 9.2 system_runs

Cada boot cria uma execução.

```sql
CREATE TABLE system_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    stopped_at TEXT,
    shutdown_clean INTEGER NOT NULL DEFAULT 0,
    version TEXT NOT NULL,
    pid INTEGER,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
```

Permite detectar:

```text
último run
+
shutdown_clean = 0
=
shutdown anterior incorreto
```

## 9.3 events

```sql
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    run_id TEXT,
    task_id TEXT,
    project_id TEXT,
    agent_id TEXT,
    severity TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY(run_id) REFERENCES system_runs(run_id)
);
```

Índices:

```sql
CREATE INDEX idx_events_type_time
ON events(event_type, timestamp);

CREATE INDEX idx_events_task_time
ON events(task_id, timestamp);
```

## 9.4 tasks

```sql
CREATE TABLE tasks (
    task_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 50,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    checkpoint_seq INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    last_error TEXT
);
```

Estados permitidos inicialmente:

```text
created
planning
ready
running
paused
blocked
verifying
completed
failed
cancelled
interrupted
```

## 9.5 task_checkpoints

```sql
CREATE TABLE task_checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    state_json TEXT NOT NULL,
    reason TEXT,
    FOREIGN KEY(task_id) REFERENCES tasks(task_id)
        ON DELETE CASCADE,
    UNIQUE(task_id, sequence)
);
```

## 9.6 system_kv

```sql
CREATE TABLE system_kv (
    key TEXT PRIMARY KEY,
    value_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

Uso futuro:

- schema metadata;
- flags;
- recovery cursor;
- maintenance state.

Não usar para secrets.

---

# 10. Event Envelope

Contrato:

```python
@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    timestamp: str
    severity: str
    run_id: str | None = None
    task_id: str | None = None
    project_id: str | None = None
    agent_id: str | None = None
    payload: dict = field(default_factory=dict)
```

`event_id`:

UUID.

`timestamp`:

UTC ISO-8601.

---

# 11. Event Bus

Primeira implementação:

```text
asyncio
+
subscriptions em memória
+
persistência opcional por subscriber
```

Contrato:

```python
class EventBus:
    async def publish(self, event: Event) -> None: ...
    async def subscribe(self, event_type, handler) -> Subscription: ...
    async def close(self) -> None: ...
```

## Regras

1. um subscriber com erro não derruba os demais;
2. erro de subscriber gera evento/log;
3. publicação preserva ordem dentro do processo;
4. eventos críticos são persistidos;
5. handlers lentos não devem bloquear indefinidamente o loop.

Na Phase 0 não existe broker externo.

---

# 12. Task Model

```python
@dataclass
class Task:
    task_id: str
    title: str
    objective: str
    status: TaskStatus
    priority: int
    created_at: datetime
    updated_at: datetime
    checkpoint_seq: int
    metadata: dict
    last_error: str | None
```

TaskStatus será Enum.

Transições são explicitamente validadas.

Exemplo:

```text
created → planning
planning → ready
ready → running
running → paused
running → verifying
verifying → completed
running → failed
running → interrupted
interrupted → ready/running/failed
```

Não permitir:

```text
completed → running
```

sem uma operação explícita de clone/reopen futura.

---

# 13. Task Service

API:

```python
create_task(...)
get_task(...)
list_tasks(...)
transition(...)
checkpoint(...)
mark_interrupted(...)
list_resumable(...)
```

`transition()`:

1. valida estado atual;
2. valida estado destino;
3. atualiza banco;
4. publica evento;
5. retorna Task atualizada.

---

# 14. Checkpoint

Um checkpoint deve registrar um snapshot mínimo.

Exemplo:

```json
{
  "step": "research",
  "progress": 0.64,
  "artifacts": [],
  "dependencies": [],
  "resume_token": null
}
```

Na Phase 0 ainda não há execução de verdade.

Testaremos com tasks simuladas.

---

# 15. Lifecycle

## Boot

```text
main()
 ↓
resolve_data_dir()
 ↓
acquire_single_instance_lock()
 ↓
configure_logging()
 ↓
load_config()
 ↓
open_database()
 ↓
apply_migrations()
 ↓
create system_run
 ↓
detect_unclean_shutdown()
 ↓
recover_tasks()
 ↓
start EventBus
 ↓
health_check()
 ↓
publish system.ready
 ↓
wait
```

## Shutdown

```text
signal
 ↓
publish system.shutdown
 ↓
stop accepting work
 ↓
flush events
 ↓
checkpoint running tasks when applicable
 ↓
close EventBus
 ↓
mark system_run shutdown_clean=1
 ↓
close database
 ↓
release lock
```

---

# 16. Single Instance

A Phase 0 deve impedir dois `jarvisd` usando o mesmo data directory.

Arquivo:

```text
runtime/instance.lock
```

Deve conter:

```json
{
  "pid": 1234,
  "run_id": "...",
  "started_at": "..."
}
```

No boot:

- lock existe;
- PID existe;
- processo corresponde ao Jarvis;

→ rejeitar nova instância.

Lock órfão:

→ registrar;
→ remover com segurança;
→ continuar.

---

# 17. Health Check

Objeto interno:

```json
{
  "status": "healthy",
  "run_id": "...",
  "uptime_seconds": 128,
  "database": "healthy",
  "event_bus": "healthy",
  "task_repository": "healthy",
  "recovery": {
    "interrupted_found": 0
  }
}
```

Estados:

```text
healthy
degraded
unhealthy
```

Na Phase 0 pode ser exibido no terminal.

UI chegará depois.

---

# 18. Logging

Formato JSON Lines.

Exemplo:

```json
{
  "timestamp":"...",
  "level":"INFO",
  "component":"bootstrap",
  "event":"database_ready",
  "run_id":"..."
}
```

Regras:

- logs humanos podem existir no console;
- arquivo é estruturado;
- traceback em erros;
- nunca logar secrets;
- cada task futura deve carregar `task_id`.

---

# 19. Crash Recovery

No próximo boot:

1. encontrar `system_runs.shutdown_clean = 0`;
2. localizar tasks em:
   - running;
   - planning;
   - verifying;
3. marcar como `interrupted`;
4. recuperar último checkpoint;
5. classificar como resumível ou não;
6. publicar eventos de recovery.

Na Phase 0:

```text
resume automático = simulado
```

Não executar efeitos externos.

---

# 20. Migration Engine

Formato:

```text
0001_foundation.sql
0002_x.sql
...
```

Algoritmo:

1. ler migration aplicada;
2. ordenar arquivos;
3. iniciar transação;
4. aplicar próxima;
5. registrar em schema_migrations;
6. commit;
7. rollback em erro.

Nunca modificar migration já aplicada.

Nova alteração = nova migration.

---

# 21. Error Taxonomy

Base:

```text
JarvisError
├── ConfigError
├── StorageError
├── MigrationError
├── StateTransitionError
├── RecoveryError
├── LockError
└── LifecycleError
```

Erros esperados devem ser tipados.

Evitar:

```python
except Exception:
    pass
```

no core.

---

# 22. Testes obrigatórios

## 22.1 Unit

### Event Bus

- publish chega ao subscriber;
- subscriber pode filtrar;
- subscriber quebrado não derruba bus;
- unsubscribe funciona.

### Config

- defaults;
- TOML;
- env override;
- caminho relativo;
- config inválida.

### Task State

- transições permitidas;
- transições proibidas;
- terminal states.

---

# 23. Integration Tests

## Database

- cria DB;
- ativa WAL;
- migrations;
- reopen;
- foreign keys;
- rollback.

## Event Persistence

- evento publicado;
- evento persistido;
- payload preservado;
- consulta por task.

## Checkpoints

- sequência correta;
- múltiplos checkpoints;
- reopen;
- último checkpoint correto.

---

# 24. Recovery Tests

## Unclean Shutdown

Simular:

```text
run criado
shutdown_clean = 0
task = running
checkpoint = 3
processo morre
```

Próximo boot deve:

```text
detectar run incompleto
marcar task interrupted
encontrar checkpoint 3
publicar recovery event
```

## Clean Shutdown

Não deve gerar falso recovery.

---

# 25. Acceptance Test

A Phase 0 só passa quando este cenário funcionar:

```text
1. iniciar Jarvis
2. criar task
3. mover task para running
4. criar checkpoint 1
5. criar checkpoint 2
6. simular crash
7. iniciar novamente
8. detectar crash
9. localizar task interrompida
10. recuperar checkpoint 2
11. finalizar task simulada
12. fechar corretamente
13. iniciar novamente
14. nenhum recovery indevido
15. health = healthy
```

---

# 26. Stress mínimo

Antes de Phase 1:

## Boot Loop

```text
50 boots limpos
```

Sem:

- corrupção;
- locks órfãos;
- migration duplicada;
- leak óbvio.

## Task Test

Criar:

```text
10.000 tasks simuladas
```

e verificar queries principais.

## Event Test

Publicar:

```text
100.000 eventos simulados
```

Não precisa ser benchmark extremo.

Objetivo é detectar arquitetura ruim cedo.

---

# 27. Critérios de aprovação da Phase 0

Todos obrigatórios:

- [ ] estrutura de projeto limpa;
- [ ] um único `.venv`;
- [ ] data directory separado;
- [ ] SQLite WAL;
- [ ] migration engine;
- [ ] Event Bus;
- [ ] event persistence;
- [ ] Task Repository;
- [ ] Task State Machine;
- [ ] checkpoints;
- [ ] system runs;
- [ ] shutdown limpo;
- [ ] recovery de shutdown incorreto;
- [ ] single-instance;
- [ ] health;
- [ ] logs estruturados;
- [ ] unit tests;
- [ ] integration tests;
- [ ] recovery tests;
- [ ] acceptance test;
- [ ] 50 boots;
- [ ] documentação;
- [ ] zero LLM;
- [ ] zero UI;
- [ ] zero automação.

---

# 28. Commits previstos

Usar commits pequenos.

```text
chore: initialize Jarvis Next foundation
feat: add runtime configuration
feat: add sqlite storage and migrations
feat: add structured event model
feat: add event bus
feat: add persistent event repository
feat: add task state machine
feat: add task repository
feat: add task checkpoints
feat: add lifecycle and system runs
feat: add crash recovery
feat: add single-instance runtime lock
feat: add health service
test: add phase0 unit tests
test: add phase0 integration tests
test: add phase0 recovery tests
test: add phase0 acceptance suite
docs: complete phase0 foundation
```

Não precisa seguir exatamente um commit por linha, mas evitar um commit gigantesco.

---

# 29. O que não devemos fazer durante a Phase 0

Não adicionar “só porque será útil depois”:

```text
Ollama
Qwen
PySide
QML
WebSocket
FastAPI
LangChain
LangGraph
Playwright
WhatsApp
ElevenLabs
OpenAI
MCP
A2A
vector database
Redis
Docker
Supabase
Vercel
```

A única pergunta da Phase 0 é:

> O núcleo consegue preservar estado corretamente e sobreviver a falhas?

---

# 30. O primeiro comando do novo Jarvis

Depois da implementação, a experiência de desenvolvimento será:

```powershell
python -m jarvis
```

Saída esperada:

```text
JARVIS NEXT
Foundation Runtime

Database............. OK
Migrations........... OK
Event Bus............ OK
Task Repository...... OK
Recovery............. OK

Run: 4f7...
Status: HEALTHY

Jarvis Core ready.
```

CTRL+C:

```text
Shutdown requested
Flushing events...
Closing task repository...
Marking run clean...
Releasing lock...

Jarvis stopped safely.
```

---

# 31. Phase 0 Definition of Done

A Phase 0 termina quando pudermos afirmar:

> “Ainda não existe IA dentro do Jarvis, mas já existe um sistema confiável onde uma IA pode viver.”

Somente então começa a Phase 1 — Brain.
