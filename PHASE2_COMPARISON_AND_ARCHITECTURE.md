# Sind-AI vs. grandes agentes — direção arquitetural

Data de referência: setembro de 2026.

## O que os grandes sistemas fazem bem

### ChatGPT Work / Codex

Pontos relevantes observados na documentação pública atual:

- tarefas longas, multi-etapas e entregáveis concluídos;
- apps/plugins conectados;
- navegador em nuvem separado;
- tarefas agendadas e acionadas por eventos;
- memória de preferências/projetos;
- uso do computador no Windows;
- contexto de janela/app (“appshots” no Codex);
- trabalhos que podem continuar e ser acompanhados remotamente.

O Sind-AI já possui vários equivalentes locais: Long-Horizon, Automation Engine, Connectors, Browser Agent, Projects, Memory, Mobile Companion e desktop access. A lacuna principal era o contexto operacional pessoal contínuo e a aprendizagem procedural baseada no uso real.

### Claude / computer use

A arquitetura de computer use combina screenshot + mouse/teclado e enfatiza uma fronteira de segurança contra prompt injection. O Sind-AI não deve copiar a abordagem visual como único mecanismo; ela deve ser fallback. Para um computador local sem GPU dedicada, APIs/eventos estruturados devem ter prioridade.

### Gemini Computer Use

A direção pública do Gemini é integrar computer-use ao modelo principal para tarefas longas em browser/mobile/desktop. Para o Sind-AI, o equivalente funcional pode ser alcançado sem um modelo multimodal pesado sempre ativo: o Observer fornece contexto barato e um VLM pode ser chamado somente quando UIA/API não bastarem.

### Microsoft UFO²/UFO³

É a referência mais próxima para a arquitetura desejada:

- HostAgent orquestra;
- AppAgents são especialistas por aplicação;
- execução híbrida GUI + API;
- documentos de ajuda como conhecimento;
- demonstrações humanas;
- experiências anteriores recuperadas por RAG.

A Fase 2 inicia essa direção com `app_expertise()`, memória procedural e recuperação de procedimentos. Também separa a janela do próprio Jarvis do último aplicativo externo usado, evitando que o chat apague o contexto de trabalho no momento em que o usuário pede ajuda.

### OpenHands

A principal lição é separar raciocínio de runtime e manter execução verificável/isolada. O Sind-AI já tem brokers, TaskStore, verifier e Long-Horizon, mas a longo prazo deve aumentar isolamento para código/experimentos e manter desktop real como camada de execução autorizada.

## Matriz resumida

| Capacidade | ChatGPT/Codex | Claude | Gemini | UFO | Sind-AI após Fase 2 |
|---|---|---|---|---|---|
| Conversa persistente | forte | forte | forte | secundário | existente |
| Memória pessoal | forte | ferramenta/memória | forte | experiência/RAG | existente + procedural |
| Computer use | forte | forte | forte | forte | existente |
| Trabalho longo | forte | agente/tools | forte | orquestrado | Long-Horizon |
| Apps conectados | plugins | MCP/tools | tools | MCP/native APIs | Connectors/services |
| Contexto do desktop | app/window/computer use | screenshots | computer use | UI state | Observer + operational context |
| Aprender demonstração humana | limitado como produto geral | não é foco central | não é foco central | forte | existente + procedural memory |
| Aprender rotina pessoal por app | parcial | parcial | parcial | forte | fundação criada |
| Operação local-first | parcial | depende integração | depende integração | Windows local | forte |
| Zero API paga obrigatória | não | não | não | depende modelo | objetivo do projeto |

## A vantagem potencial do Sind-AI

O objetivo não é vencer modelos de fronteira em inteligência geral. O diferencial é possuir um contexto operacional pessoal que os modelos gerais normalmente não têm de forma permanente:

`seus projetos + seus arquivos + seus aplicativos + suas demonstrações + suas correções + suas integrações + seus processos`.

Um modelo menor com esse contexto e ferramentas corretas pode ser mais útil em rotinas pessoais específicas do que um modelo muito maior que começa cada tarefa sem conhecer o processo local.

## Arquitetura-alvo

```text
User / Strategy
      |
      v
Jarvis Supervisor
      |
      +--------------------+
      |                    |
      v                    v
Goal/Work Manager      Personal Context Kernel
      |                    |
      |              +-----+------+
      |              |            |
      |          Episodic      Procedural
      |           Memory        Memory
      |              |            |
      +--------------+------------+
                     |
               App Expert Router
                     |
     +---------------+----------------+
     |               |                |
 Photoshop Expert  VSCode Expert   Browser Expert ...
     |               |                |
     +-------+-------+----------------+
             |
       Execution Policy
             |
    API > native bridge > UIA > vision
             |
          Computer
             |
         Verification
             |
       Experience update
```

## Fases seguintes

### Phase 3 — Photoshop Expert

Criar um bridge UXP que envie eventos estruturados para `observe.ingest_event()`. O objetivo é trocar aprendizado baseado em coordenadas por operações semânticas como selecionar camada, trocar texto, transformar, aplicar efeito e exportar.

### Phase 4 — Correction Learning

Guardar pares `resultado do Jarvis -> correção humana -> resultado aprovado`. Isso fornece exemplos pessoais de decisões, não apenas passos.

### Phase 5 — Work Manager

Transformar objetivos amplos em backlog persistente de entregáveis, dependências, critérios de sucesso e checkpoints, coordenando Long-Horizon/Workplace/Swarm.

### Phase 6 — Self Research / Capability Lab

Quando faltar capacidade: pesquisar documentação/API -> criar executor em sandbox -> testar -> verificar -> propor instalação. Nunca promover código não testado diretamente para produção.

### Phase 7 — Vision fallback

Adicionar parser visual/VLM sob demanda, não contínuo. Usar somente quando API, bridge nativo e UI Automation não conseguirem identificar a ação.

### Phase 8 — Autonomia operacional

A autonomia passa a ser medida por procedimento, com histórico real de sucesso/correção/falha. Rotinas maduras podem subir de learned -> practiced -> trusted -> autonomous.

## Referências públicas usadas nesta direção

- OpenAI — ChatGPT Work / Cloud Browser / Tasks / Codex computer use e memória.
- Anthropic — Computer Use e ferramentas de memória/tool-search.
- Google — Gemini 3.5 Flash Computer Use.
- Microsoft — UFO² AppAgent, learning from demonstrations e experience learning.
- OpenHands — runtime isolado e arquitetura de execução.
