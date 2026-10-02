# JARVIS — MASTER SPECIFICATION
## Personal Agent Operating System
**Versão:** 1.0  
**Status:** Arquitetura-base aprovada para início do projeto  
**Objetivo:** definir o produto, as regras estruturais, a arquitetura, os contratos internos e o roadmap antes da implementação.

---

# 1. Visão

Jarvis não será um chatbot local, nem apenas um agente com ferramentas.

Jarvis será um **Personal Agent Operating System**: uma inteligência central persistente, capaz de conversar, observar fontes autorizadas, lembrar contexto, organizar projetos, delegar trabalho, executar tarefas, verificar resultados, adquirir novas capacidades e trabalhar continuamente em segundo plano.

A experiência deve combinar:

- **Companion minimalista** para o uso diário;
- **Jarvis HQ** como representação visual dos agentes e departamentos;
- **Mission Control** para acompanhar tarefas e execuções;
- **Workspace** para projetos, arquivos, memória e decisões;
- **Model Mesh** para usar diferentes modelos conforme necessidade;
- **Tool Mesh** para acessar APIs, apps, browser, arquivos e desktop;
- **Capability System** para adquirir novas competências sem modificar o núcleo em produção.

O sistema deverá ser **local-first**, funcionar sem assinatura sempre que possível e permitir serviços externos apenas como melhorias opcionais.

---

# 2. Resultado esperado

Ao ligar o computador:

1. o serviço principal inicia automaticamente;
2. restaura estado, tarefas e memória;
3. consulta fontes autorizadas;
4. atualiza agenda, mensagens, e-mails, projetos e jobs;
5. gera um briefing;
6. abre o Companion;
7. cumprimenta o usuário e apresenta o que merece atenção.

Exemplo:

> Bom dia. Você tem duas mensagens importantes, uma reunião às 11h e uma entrega concluída durante a madrugada. A pesquisa da campanha CCT terminou e está aguardando sua revisão.

Durante o dia, o usuário poderá dizer:

> Jarvis, prepare uma nova campanha sobre data-base.

Jarvis deverá:

1. interpretar o objetivo;
2. recuperar contexto e memória relevantes;
3. decompor a missão;
4. selecionar agentes;
5. montar a equipe;
6. distribuir tarefas;
7. executar;
8. acompanhar progresso;
9. solicitar aprovação quando necessário;
10. verificar a entrega;
11. registrar os resultados;
12. aprender com feedback;
13. apresentar a entrega final.

---

# 3. Princípios constitucionais

Estas regras não são prompts. Devem existir na arquitetura.

## 3.1 Execução

**SEM AÇÃO REAL, NÃO HOUVE EXECUÇÃO.**

Um modelo não pode declarar que uma ação foi realizada apenas porque pretendia realizá-la.

## 3.2 Verificação

**SEM EVIDÊNCIA, NÃO HOUVE SUCESSO.**

Toda ação relevante deve ter uma etapa de verificação independente.

Estados válidos:

- `completed`
- `failed`
- `uncertain`
- `blocked`
- `waiting_approval`

Nunca transformar incerteza em sucesso.

## 3.3 Durabilidade

**SEM CHECKPOINT, NÃO HÁ TAREFA DURÁVEL.**

Jobs longos devem poder sobreviver a:

- fechamento da UI;
- queda do modelo;
- erro de ferramenta;
- reinício do Jarvis;
- reinício do computador.

## 3.4 Memória

**SEM FONTE, NÃO É MEMÓRIA CONFIÁVEL.**

Toda memória persistente deve registrar:

- origem;
- data;
- confiança;
- escopo;
- projeto;
- importância;
- possibilidade de expiração.

## 3.5 Permissões

**SEM PERMISSÃO, NÃO HÁ EFEITO EXTERNO.**

Cada ferramenta e ação deve possuir política de autorização.

## 3.6 Resiliência

**NENHUMA FUNÇÃO OPCIONAL PODE IMPEDIR O JARVIS DE INICIAR.**

Exemplos:

- ElevenLabs indisponível → Jarvis continua;
- modelo secundário indisponível → Jarvis continua;
- connector offline → Jarvis continua;
- HQ visual com erro → Companion continua.

## 3.7 Núcleo protegido

**JARVIS PODE CRIAR SKILLS. JARVIS NÃO PODE ALTERAR O CORE EM PRODUÇÃO.**

Novas capacidades devem ser:

- isoladas;
- versionadas;
- testadas;
- reversíveis;
- aprováveis.

---

# 4. Identidade do produto

## 4.1 Jarvis é uma entidade única

O usuário conversa com **Jarvis**.

Research, Analyst, Creator, Operator etc. são componentes internos.

O usuário não precisa gerenciar múltiplos chats.

## 4.2 A orb representa Jarvis

A orb é a identidade visual da inteligência central.

Ela reage a estados reais:

- `idle`
- `listening`
- `thinking`
- `planning`
- `delegating`
- `acting`
- `verifying`
- `waiting_approval`
- `speaking`
- `completed`
- `blocked`
- `error`

A orb não deve ser apenas decoração.

## 4.3 O escritório representa as mãos do Jarvis

O Jarvis HQ representa:

- departamentos;
- agentes;
- missões;
- handoffs;
- bloqueios;
- aprovações;
- entregas.

Toda animação relevante deve corresponder a eventos reais do backend.

---

# 5. Superfícies do sistema

## 5.1 Companion

Tela cotidiana.

Características:

- minimalista;
- rápida;
- orb;
- chat;
- voz;
- poucos widgets;
- briefing;
- notificações;
- acesso ao HQ.

O Companion não deve parecer um dashboard.

Exemplo visual:

```text
                 ●
               JARVIS

Bom dia.
Há 3 coisas que merecem sua atenção.

2 emails importantes
Reunião às 11h
1 entrega pronta

[ Pergunte qualquer coisa... ]

[ Abrir HQ ]
```

## 5.2 Jarvis HQ

A experiência visual mais rica.

Formato:

- escritório isométrico;
- departamentos;
- personagens;
- salas;
- mesas;
- núcleo central;
- atividade em tempo real.

Departamentos iniciais:

- Command
- Research
- Intelligence
- Creative
- Engineering
- Operations
- Review
- Administration
- Memory

O HQ não deve controlar a lógica. Ele apenas observa e envia comandos ao Core.

## 5.3 Mission Control

Tela operacional de uma missão.

Mostra:

- objetivo;
- plano;
- equipe;
- agentes;
- etapas;
- progresso;
- artifacts;
- logs;
- bloqueios;
- aprovações;
- custo;
- recursos;
- evidências.

## 5.4 Workspace

Organização por projeto.

Cada workspace contém:

- objetivos;
- contexto;
- tarefas;
- arquivos;
- decisões;
- memória;
- agentes;
- artifacts;
- histórico;
- regras;
- permissões específicas.

## 5.5 Agent Directory

Catálogo de agentes disponíveis.

Cada agente possui:

- identidade;
- departamento;
- missão;
- capacidades;
- ferramentas;
- modelos preferidos;
- política de risco;
- entradas;
- saídas;
- métricas;
- versão.

## 5.6 Memory

Tela de transparência sobre o que foi aprendido.

Categorias:

- preferências;
- fatos;
- projetos;
- pessoas;
- procedimentos;
- decisões;
- padrões;
- feedback;
- aprendizados recentes.

## 5.7 System

Configurações técnicas:

- modelos;
- ferramentas;
- conectores;
- permissões;
- computadores;
- voz;
- jobs;
- segurança;
- plugins;
- health checks.

---

# 6. Topologia de processos

O Jarvis não deve depender da interface gráfica.

## 6.1 jarvisd

Processo principal persistente.

Responsável por:

- event bus;
- task engine;
- agent runtime;
- memory;
- model mesh;
- tool mesh;
- approvals;
- scheduler;
- watchers;
- health;
- persistence.

`jarvisd` inicia com o Windows.

## 6.2 jarvis-ui

Interface.

Conecta-se ao `jarvisd` por IPC/WebSocket local.

Pode fechar sem interromper jobs.

## 6.3 workers

Processos isolados para:

- agentes;
- ferramentas arriscadas;
- browser;
- sandbox;
- código;
- tarefas longas.

## 6.4 Relação

```text
Windows
  │
  └── jarvisd
       │
       ├── Event Bus
       ├── Task Engine
       ├── Memory
       ├── Model Mesh
       ├── Tool Mesh
       ├── Scheduler
       └── Workers
            │
            ├── Agent Worker
            ├── Browser Worker
            ├── Desktop Worker
            └── Sandbox Worker

jarvis-ui
  │
  └──── localhost IPC ──── jarvisd
```

---

# 7. Event Bus

O Event Bus será o sistema nervoso do Jarvis.

## 7.1 Regra

Nenhuma UI deve depender diretamente de um agente.

Agentes e ferramentas publicam eventos.

A UI observa eventos.

## 7.2 Eventos principais

```text
system.started
system.ready
system.degraded
system.shutdown

connector.sync.started
connector.sync.completed
connector.sync.failed

briefing.started
briefing.completed

project.created
project.updated

task.created
task.planned
task.started
task.paused
task.resumed
task.completed
task.failed
task.blocked

agent.selected
agent.spawned
agent.started
agent.progress
agent.completed
agent.failed
agent.retired

artifact.created
artifact.updated
artifact.approved

tool.requested
tool.started
tool.completed
tool.failed

verification.started
verification.passed
verification.failed
verification.uncertain

approval.required
approval.approved
approval.rejected

memory.proposed
memory.committed
memory.updated
memory.expired

skill.discovered
skill.generated
skill.testing
skill.approved
skill.installed
skill.disabled

voice.listening
voice.processing
voice.speaking
voice.idle
```

## 7.3 Envelope padrão

```json
{
  "event_id": "uuid",
  "event_type": "agent.started",
  "timestamp": "ISO-8601",
  "task_id": "uuid",
  "project_id": "uuid",
  "agent_id": "research.web",
  "severity": "info",
  "payload": {}
}
```

---

# 8. Task Engine

A missão é a unidade principal de trabalho.

## 8.1 Estados

```text
created
planning
ready
running
waiting_dependency
waiting_approval
paused
blocked
verifying
completed
failed
cancelled
```

## 8.2 Ciclo

```text
OBJECTIVE
   ↓
PLAN
   ↓
TEAM
   ↓
EXECUTE
   ↓
OBSERVE
   ↓
VERIFY
   ↓
DELIVER
   ↓
LEARN
```

## 8.3 Checkpoints

Cada etapa deve poder persistir:

- estado;
- input;
- output;
- artifacts;
- agentes;
- ferramentas;
- erros;
- dependências;
- progresso.

## 8.4 Tarefa exemplo

```json
{
  "id": "task-184",
  "title": "Campanha Data-Base",
  "objective": "Criar uma campanha completa",
  "status": "running",
  "project_id": "marketing-2026",
  "priority": 70,
  "created_at": "...",
  "checkpoint": 4,
  "team_id": "team-52",
  "approval_policy": "workspace_default"
}
```

---

# 9. Agentes

## 9.1 Conceito

Um agente não é necessariamente um LLM.

Pode ser:

- LLM;
- código determinístico;
- LLM + ferramentas;
- pipeline;
- visão;
- SQL;
- browser;
- UI Automation;
- combinação.

## 9.2 Hierarquia

```text
JARVIS
  │
  ├── Research Director
  ├── Intelligence Director
  ├── Creative Director
  ├── Engineering Director
  ├── Operations Director
  ├── Review Director
  └── Administration Director
```

Managers dividem trabalho.

Especialistas executam.

## 9.3 Departamentos

### Research

- Web Researcher
- Document Researcher
- Legal Researcher
- Market Researcher
- Competitor Researcher
- Social Researcher
- Source Validator

### Intelligence

- Data Analyst
- Business Analyst
- Document Analyst
- Risk Analyst
- Performance Analyst
- Planning Analyst

### Creative

- Strategist
- Copywriter
- Social Media Planner
- Reels Planner
- Script Writer
- SEO Writer
- Visual Planner

### Engineering

- Software Architect
- Python Developer
- Frontend Developer
- Backend Developer
- Database Engineer
- API Integrator
- Automation Engineer
- Windows Specialist
- QA Engineer
- Security Engineer

### Operations

- Desktop Operator
- Browser Operator
- File Operator
- Email Operator
- WhatsApp Operator
- CMS Operator
- Spreadsheet Operator

### Review

- Verifier
- Fact Checker
- Quality Reviewer
- Security Reviewer
- Brand Reviewer

### Administration

- Calendar Agent
- Inbox Agent
- Meeting Prep
- Follow-up Agent
- Scheduler
- Reminder Agent

## 9.4 Agent Card

```yaml
id: marketing.instagram.strategy
name: Instagram Strategist
department: creative

mission:
  Planejar conteúdo de Instagram.

capabilities:
  - analytics_read
  - web_research
  - memory_read

tools:
  - browser
  - files

model_requirements:
  reasoning: medium
  vision: optional

permissions:
  external_write: false
  publish: false

inputs:
  - campaign_goal
  - analytics
  - brand_context

outputs:
  - content_plan

review:
  required: true
```

---

# 10. Agent Factory

O sistema deve permitir agentes temporários.

Exemplo:

```text
Necessidade:
"Analisar tabelas específicas de contratos PDF"

↓ nenhum agente ideal

Agent Factory

↓ cria

Temporary Agent:
PDF Contract Structure Analyst

↓ executa tarefa

↓ mede desempenho

Se útil repetidamente:
propor incorporação permanente
```

Agentes temporários nunca recebem permissões superiores às da missão.

---

# 11. Model Mesh

O Jarvis não pertence a um modelo.

## 11.1 Interface

Todo modelo deve implementar contrato equivalente a:

```text
chat()
stream()
tool_call()
vision()
embed()
health()
metadata()
```

## 11.2 Metadados

```text
provider
model
local/cloud
modalities
reasoning
coding
vision
tool_use
context_window
latency
memory_cost
gpu_cost
privacy_level
monetary_cost
reliability
```

## 11.3 Routing

Exemplo:

```text
ação simples
→ modelo pequeno

conversa comum
→ modelo rápido

análise complexa
→ reasoning

imagem
→ vision

código
→ coding

privacidade alta
→ local only

budget free
→ modelos gratuitos/local
```

## 11.4 Model Benchmarking

O Jarvis poderá avaliar modelos com tarefas reais.

Métricas:

- qualidade;
- tempo;
- memória;
- falhas;
- custo;
- tool calling;
- aderência às instruções.

O router pode aprender qual modelo funciona melhor para cada classe de tarefa.

---

# 12. Tool Mesh

Ferramentas são capacidades externas.

## 12.1 Prioridade de interação

```text
1. API nativa
2. MCP
3. integração estruturada
4. browser DOM
5. Windows UI Automation
6. visão + mouse/teclado
```

Visão e coordenadas são último recurso.

## 12.2 Tool Descriptor

```yaml
id: whatsapp.send_message

risk: external_write

inputs:
  recipient: string
  message: string

verification:
  required: true

permissions:
  default: approval

executor:
  type: windows_uia
```

---

# 13. Verificação

O executor e o verificador devem ser logicamente separados.

Exemplo:

```text
Operator
  ↓
envia mensagem
  ↓
Verifier
  ↓
reabre/observa
  ↓
mensagem encontrada?

YES → completed
NO → failed
? → uncertain
```

A verificação deve usar evidência apropriada:

- arquivo existe;
- conteúdo mudou;
- elemento aparece;
- API confirmou;
- mensagem aparece;
- status remoto retornou;
- checksum;
- screenshot;
- resposta HTTP.

---

# 14. Aprovações e permissões

## 14.1 Níveis

### Read

Exemplos:

- ler arquivo;
- consultar email;
- consultar calendário.

Padrão: automático.

### Prepare

Exemplos:

- escrever rascunho;
- preparar documento;
- montar mensagem.

Padrão: automático.

### Internal Write

Exemplos:

- editar arquivo;
- organizar workspace.

Padrão: configurável.

### External Write

Exemplos:

- enviar email;
- enviar WhatsApp;
- publicar conteúdo;
- alterar site.

Padrão: aprovação.

### Destructive

Exemplos:

- excluir;
- substituir;
- revogar;
- resetar.

Padrão: aprovação forte.

### Financial / Credential

Exemplos:

- comprar;
- transferir;
- alterar senha;
- credenciais.

Padrão: bloqueado ou manual.

## 14.2 Policy

```yaml
action: whatsapp.send
scope: team_contacts
mode: auto
conditions:
  - business_hours
  - template_approved
```

---

# 15. Memória

Não existe uma memória única.

## 15.1 Tipos

### Working
Contexto da execução atual.

### Episodic
O que aconteceu.

### Semantic
Fatos duráveis.

### Preferences
Preferências do usuário.

### Procedural
Como fazer algo.

### Project
Contexto de projetos.

### Relationship
Pessoas, organizações e relações.

### Artifact
Produtos criados.

## 15.2 Registro

```json
{
  "id": "memory-uuid",
  "type": "preference",
  "content": "Prefere interfaces minimalistas.",
  "source": "conversation",
  "source_ref": "...",
  "confidence": 0.96,
  "scope": "global",
  "project_id": null,
  "importance": 0.8,
  "created_at": "...",
  "expires_at": null
}
```

## 15.3 Memory Curator

Processo responsável por:

- deduplicar;
- consolidar;
- detectar conflito;
- atualizar confiança;
- expirar;
- promover informações importantes.

Não treina modelo.

Organiza conhecimento.

---

# 16. Workspace

Estrutura lógica:

```text
Workspace
  ├── objectives
  ├── tasks
  ├── artifacts
  ├── sources
  ├── decisions
  ├── memory
  ├── agents
  ├── permissions
  └── history
```

Cada workspace deve poder possuir regras próprias.

---

# 17. Capability Resolver

Quando o Jarvis não souber fazer algo:

```text
REQUEST
  ↓
Skill Registry
  ↓
Tool Registry
  ↓
MCP
  ↓
Agent Registry
  ↓
Research
  ↓
Capability Builder
  ↓
Sandbox
  ↓
Tests
  ↓
Security Review
  ↓
Approval
  ↓
Install
```

O Jarvis nunca deve simplesmente editar o próprio core.

---

# 18. Skills

Uma skill contém:

```text
manifest
executor
tests
permissions
version
documentation
rollback
```

Estrutura:

```text
skills/
  example_skill/
    manifest.yaml
    executor.py
    tests/
    README.md
```

Estados:

- discovered
- generated
- testing
- approved
- active
- disabled
- deprecated

---

# 19. Morning Briefing

## 19.1 Fontes

Conforme autorização:

- email;
- calendário;
- mensagens;
- projetos;
- tarefas;
- jobs;
- watchers;
- notícias específicas;
- sistemas internos.

## 19.2 Pipeline

```text
STARTUP
  ↓
SYNC DELTAS
  ↓
CLASSIFY
  ↓
PRIORITIZE
  ↓
CONNECT PROJECT CONTEXT
  ↓
BRIEFING
  ↓
VOICE + COMPANION
```

## 19.3 Regras

Briefing deve destacar apenas o que merece atenção.

Não gerar uma lista gigante.

---

# 20. Watchers

Watchers observam condições futuras.

Exemplos:

- novo email importante;
- alteração de calendário;
- resposta esperada;
- job concluído;
- site alterado;
- prazo próximo;
- arquivo novo;
- atualização de sistema.

Watcher não é necessariamente um agente.

Pode ser lógica determinística.

---

# 21. Scheduler

Responsável por:

- jobs recorrentes;
- briefing;
- manutenção;
- memória;
- backups;
- watchers;
- análises programadas.

Scheduler deve criar tasks pelo mesmo Task Engine.

Nada de caminho paralelo.

---

# 22. Voz

Voz é uma camada.

Jarvis deve funcionar sem ela.

## 22.1 Entrada

- STT local como base;
- provider externo opcional.

## 22.2 Saída

Prioridade:

```text
TTS local neural
↓
provider externo opcional
↓
texto
```

Nenhum TTS pode impedir inicialização.

---

# 23. Interface

## 23.1 Tecnologia

Meta inicial:

- desktop Windows;
- PySide6;
- QML;
- renderização GPU;
- comunicação por WebSocket/IPC.

Evitar WebView como fundação principal.

## 23.2 Estilo

Companion:

- minimalista;
- poucas bordas;
- pouco texto;
- foco no Jarvis.

HQ:

- isométrico;
- mais rico;
- visual lúdico;
- altamente observável.

## 23.3 Regra

Toda informação visual deve ter origem em estado real.

Nada de “agente trabalhando” se nenhum worker está trabalhando.

---

# 24. Persistência

Meta inicial:

- SQLite;
- WAL;
- migrações;
- event log.

Bancos lógicos:

```text
system.db
events.db
tasks.db
memory.db
projects.db
agents.db
artifacts.db
skills.db
permissions.db
```

Podem começar no mesmo arquivo físico, desde que os domínios sejam separados.

---

# 25. Secrets

Nunca armazenar secrets em texto puro no projeto.

No Windows:

- Credential Manager;
- DPAPI;
- secret store local.

O modelo não deve receber credenciais.

Ferramentas acessam secrets por referência.

---

# 26. Observabilidade

Cada ação deve registrar:

- task;
- agent;
- tool;
- duração;
- input sanitizado;
- output;
- status;
- evidência;
- erros;
- modelo;
- recursos.

Deve existir uma Activity View.

---

# 27. Segurança

## 27.1 Sandbox

Código criado pelo Jarvis roda primeiro em sandbox.

## 27.2 Least Privilege

Agentes recebem somente ferramentas necessárias.

## 27.3 Credentials Isolation

Modelo não acessa segredo diretamente.

## 27.4 Prompt Injection

Conteúdo externo nunca pode automaticamente elevar permissão.

## 27.5 Kill Switch

Usuário deve possuir:

- Pause All;
- Stop Task;
- Disable Tool;
- Disable Agent;
- Offline Mode.

---

# 28. Crash Recovery

Ao iniciar:

```text
load database
↓
validate schema
↓
load unfinished tasks
↓
validate checkpoints
↓
mark interrupted workers
↓
resume eligible jobs
↓
request intervention for unsafe jobs
```

A UI não participa deste processo.

---

# 29. Estrutura de pastas

```text
Jarvis/
│
├── app/
│   ├── daemon.py
│   ├── bootstrap.py
│   └── lifecycle.py
│
├── core/
│   ├── events/
│   ├── tasks/
│   ├── agents/
│   ├── approvals/
│   └── policies/
│
├── models/
│   ├── base.py
│   ├── registry.py
│   ├── router.py
│   └── providers/
│
├── memory/
│   ├── store.py
│   ├── retrieval.py
│   └── curator.py
│
├── tools/
│   ├── registry.py
│   ├── files/
│   ├── browser/
│   ├── windows/
│   └── connectors/
│
├── agents/
│   ├── registry/
│   ├── managers/
│   └── factory/
│
├── runtime/
│   ├── executor.py
│   ├── observer.py
│   ├── verifier.py
│   ├── workers.py
│   └── sandbox.py
│
├── scheduler/
│   ├── scheduler.py
│   └── watchers/
│
├── workspaces/
│
├── skills/
│
├── storage/
│   ├── database.py
│   ├── migrations/
│   └── repositories/
│
├── ipc/
│   ├── server.py
│   └── protocol.py
│
├── ui/
│   ├── qml/
│   ├── companion/
│   ├── hq/
│   ├── mission_control/
│   └── assets/
│
├── voice/
│   ├── stt/
│   └── tts/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── acceptance/
│   └── recovery/
│
├── config/
│
└── docs/
```

---

# 30. Contratos obrigatórios

## Agent

```python
class Agent:
    async def plan(...)
    async def execute(...)
    async def checkpoint(...)
    async def cancel(...)
```

## Model

```python
class ModelProvider:
    async def chat(...)
    async def stream(...)
    async def health(...)
```

## Tool

```python
class Tool:
    async def execute(...)
    async def verify(...)
    def risk(...)
```

## Event Bus

```python
class EventBus:
    async def publish(...)
    async def subscribe(...)
```

## Task Repository

```python
class TaskRepository:
    create(...)
    update(...)
    checkpoint(...)
    list_resumable(...)
```

Os contratos devem depender de interfaces, não implementações concretas.

---

# 31. Performance

O sistema não deve manter dezenas de modelos ativos.

Agent Card ≠ modelo carregado.

Meta:

```text
centenas de agentes definidos
poucos workers ativos
1–2 modelos carregados normalmente
```

Workers temporários devem ser liberados ao concluir tarefas.

---

# 32. Local-first

O Jarvis deve possuir um modo:

```text
LOCAL ONLY
```

Nesse modo:

- nenhum dado sai da máquina;
- apenas modelos locais;
- apenas tools locais;
- conectores externos desabilitados.

Outro modo:

```text
HYBRID
```

Pode usar providers externos conforme policy.

---

# 33. Distributed Jarvis

Não faz parte da versão inicial.

Arquitetura deve permitir futuramente:

```text
Jarvis Core
  │
  ├── PC principal
  ├── mini-PC
  ├── notebook
  ├── servidor
  └── cloud worker
```

Cada node anuncia capacidades.

O Task Engine distribui jobs.

---

# 34. Autonomia

Autonomia não significa agir sem controle.

Níveis:

## Level 0 — Reactive

Só trabalha quando solicitado.

## Level 1 — Background

Continua jobs iniciados.

## Level 2 — Watchers

Observa fontes autorizadas.

## Level 3 — Proactive Proposal

Detecta oportunidades e sugere ações.

## Level 4 — Scoped Autonomy

Executa automaticamente ações pré-autorizadas.

## Level 5 — Continuous Operations

Gerencia determinados objetivos continuamente.

Cada workspace pode ter nível diferente.

---

# 35. Métricas de agentes

Agentes devem acumular desempenho.

Exemplos:

```text
tasks_completed
tasks_failed
verification_pass_rate
avg_duration
avg_cost
user_revisions
approval_rate
tool_failures
confidence
```

Essas métricas auxiliam seleção futura.

---

# 36. Seleção de equipe

Fluxo:

```text
objective
↓
requirements
↓
skills required
↓
agent registry
↓
score
↓
team proposal
↓
resource allocation
↓
start
```

Score pode considerar:

- especialidade;
- histórico;
- ferramentas;
- disponibilidade;
- modelo;
- risco;
- custo.

---

# 37. Artifacts

Agentes não devem trocar enormes conversas.

Devem compartilhar artifacts.

Exemplos:

```text
research.md
sources.json
analysis.json
brief.md
draft.md
campaign.json
report.pdf
image.png
code.patch
```

Artifact contém:

```text
id
type
task
creator
version
path
checksum
metadata
```

---

# 38. Handoffs

Handoff:

```text
agent A
  ↓ artifact
agent B
```

O agente B recebe:

- objetivo;
- artifact;
- contexto mínimo;
- constraints.

Não recebe toda a memória interna do agente A.

---

# 39. Planejamento

Tasks simples não precisam de planejamento complexo.

Regra:

```text
deterministic action
→ direct route

short task
→ lightweight plan

complex task
→ decomposed plan

long project
→ durable project plan
```

Evitar usar LLM onde código determinístico resolve.

---

# 40. Morning Experience

Experiência-alvo:

```text
PC ON
↓
Jarvis Core já está iniciando
↓
connectors sincronizam
↓
briefing é preparado
↓
Companion aparece
↓
orb acorda
↓
"Bom dia."
↓
3–5 informações realmente importantes
↓
usuário decide por onde começar
```

Nada de dezenas de alertas na tela.

---

# 41. HQ Experience

A HQ é um ambiente visual.

Estados:

- estação apagada → idle;
- estação iluminada → working;
- amarelo → waiting;
- vermelho → blocked;
- verde → completed.

Handoff pode ser visualizado.

Artifact pode “viajar” entre setores.

Agentes podem aparecer em mesas.

Tudo ligado ao Event Bus.

---

# 42. Não objetivos da V1

Não implementar inicialmente:

- swarm irrestrito;
- autoedição de core;
- centenas de workers simultâneos;
- cloud obrigatória;
- marketplace;
- mobile completo;
- navegador próprio;
- treinamento de modelos;
- sistema distribuído;
- autonomia financeira;
- publicação automática irrestrita.

---

# 43. Roadmap

## Phase 0 — Foundation

Entregáveis:

- repositório novo;
- bootstrap;
- config;
- logger;
- SQLite;
- migrations;
- Event Bus;
- Task repository;
- health check;
- tests;
- crash-safe startup.

**Nenhum modelo.**

Critério:

- iniciar 50 vezes sem erro;
- fechar incorretamente;
- reabrir;
- banco permanecer íntegro.

---

## Phase 1 — Brain

- model interface;
- primeiro provider local;
- streaming;
- router;
- fallback;
- health.

Critério:

- conversar;
- provider cair;
- Jarvis informar degradação;
- aplicação continuar.

---

## Phase 2 — Companion

- PySide6;
- QML;
- orb;
- chat;
- minimal UI;
- IPC;
- startup Windows.

Critério:

- UI pode reiniciar sem encerrar Core;
- Core pode reiniciar e UI reconecta.

---

## Phase 3 — Memory

- conversations;
- memory schema;
- retrieval;
- provenance;
- curator básico.

Critério:

- fechar;
- reiniciar;
- recuperar contexto correto.

---

## Phase 4 — Task Engine

- durable tasks;
- checkpoints;
- worker execution;
- cancel/resume.

Critério:

- interromper tarefa no meio;
- reiniciar PC;
- continuar a partir do checkpoint.

---

## Phase 5 — Agents

- registry;
- agent cards;
- directors;
- team builder;
- artifacts;
- handoffs.

Critério:

- missão multiagente;
- artifacts rastreáveis;
- nenhum contexto perdido.

---

## Phase 6 — Jarvis HQ

- escritório visual;
- departments;
- agents;
- mission activity;
- click agent;
- status real.

Critério:

- nenhuma animação sem evento correspondente.

---

## Phase 7 — Computer Use

- files;
- browser;
- UIA;
- observer;
- verifier.

Critério:

- executar ações;
- verificar;
- não declarar sucesso sem evidência.

---

## Phase 8 — Connectors

Inicialmente read-only:

- email;
- calendar;
- files;
- outros.

Critério:

- sync incremental;
- connector falhar sem quebrar sistema.

---

## Phase 9 — Morning Briefing

- startup sync;
- prioritization;
- digest;
- voice optional.

Critério:

- briefing curto;
- útil;
- baseado em dados reais.

---

## Phase 10 — Voice

- local STT;
- local TTS;
- external providers optional.

Critério:

- voice provider falhar;
- UI e chat continuarem.

---

## Phase 11 — Approvals

- permission engine;
- policies;
- approval UI;
- audit.

Critério:

- ação externa não passa sem policy adequada.

---

## Phase 12 — Watchers & Scheduler

- recurring jobs;
- condition watchers;
- overnight work.

Critério:

- jobs sobrevivem restart.

---

## Phase 13 — Capability System

- skill registry;
- resolver;
- generator;
- sandbox;
- tests;
- install;
- rollback.

Critério:

- nova skill não consegue comprometer core.

---

## Phase 14 — Model Mesh

- múltiplos providers;
- benchmarks;
- cost/privacy routing;
- failover.

---

## Phase 15 — Distributed Jarvis

- nodes;
- remote workers;
- capability advertisement;
- job scheduling.

---

## Phase 16 — Proactivity

- opportunities;
- proactive research;
- proposals;
- scoped autonomous actions.

---

# 44. Definition of Done

Uma feature só é concluída quando possui:

- implementação;
- teste;
- erro controlado;
- logs;
- documentação;
- política de permissão;
- fallback;
- recuperação;
- UI observável quando aplicável.

---

# 45. Regra de evolução

Antes de implementar uma nova função, responder:

1. pertence a qual domínio?
2. já existe contrato adequado?
3. é agente, tool, skill ou workflow?
4. precisa de LLM?
5. qual risco?
6. como verifica?
7. como persiste?
8. como falha?
9. como recupera?
10. como desativa?

Se essas perguntas não tiverem resposta, a feature não entra.

---

# 46. Primeira versão realmente útil

O primeiro marco significativo não será “Jarvis faz tudo”.

Será:

> O computador liga, Jarvis inicia sozinho, me cumprimenta, lembra meus projetos, conversa bem, executa algumas ferramentas confiáveis, mostra o que está fazendo, verifica resultados e não quebra quando um módulo opcional falha.

Depois disso expandimos.

---

# 47. Visão de longo prazo

O objetivo final:

```text
                         USER
                           │
                           ▼
                      JARVIS CORE
                           │
            ┌──────────────┼──────────────┐
            │              │              │
         MEMORY         TASKS          POLICIES
            │              │              │
            └──────────────┼──────────────┘
                           │
                     ORCHESTRATOR
                           │
          ┌────────────────┼────────────────┐
          │                │                │
       AGENTS           MODELS            TOOLS
          │                │                │
      300+ roles       local/cloud        MCP/API/UIA
          │                │                │
          └────────────────┼────────────────┘
                           │
                       WORKERS
                           │
                  24/7 DURABLE JOBS
                           │
                         VERIFY
                           │
                          USER
```

O Jarvis deve crescer em capacidade sem crescer em fragilidade.

Essa é a principal diferença em relação ao projeto anterior.

---

# 48. Próxima ação oficial

Antes de instalar Python, Ollama, Node ou qualquer outro runtime:

1. criar o repositório base;
2. adicionar esta especificação em `/docs`;
3. definir Phase 0;
4. criar testes de arquitetura;
5. somente então instalar o mínimo necessário para Foundation.

A implementação deverá seguir a especificação — não redefini-la enquanto é construída.
