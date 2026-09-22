# Arquitetura final do protótipo

```text
USUÁRIO
  |
  v
CONVERSATION-FIRST UI
  |
  +--> Conversation Store
  +--> Project Context
  +--> Attachments
  +--> Learning Journal
  +--> Reflection Engine
  +--> Semantic Memory (opcional)
  |
  v
CONTEXT ORCHESTRATOR
  |
  v
ADAPTIVE MODEL ROUTER
  |                     |
  | FAST                | REASON
  v                     v
conversa/Q&A         planejamento/tool calling
  |                     |
  +----------+----------+
             |
             v
       AGENT RUNTIME
             |
   +---------+---------+-------------------+
   |         |         |                   |
 Public   Browser    Desktop          Knowledge
 Data       UI      / Files        / Institutional
   |         |         |                   |
   +---------+---------+-------------------+
             |
   +---------+----------+---------+
   |                    |         |
 Actions             Workflows  Skills
   |                    |         |
   +---------+----------+---------+
             |
   +---------+---------+----------+
   |                   |          |
 Automations        Monitors   Connectors
   |                   |          |
   +---------+---------+----------+
             |
         Approvals
             |
       External systems
```

## Ecossistema SindPetshop-SP

Os canais cotidianos são tratados como `InstitutionalServices`: o Jarvis recebe contexto e pode abrir/usar cada serviço conforme o pedido sem transformá-los em abas permanentes.

## Expansão

1. Public Data Scout descobre interfaces públicas.
2. Connector Gateway recebe APIs autorizadas.
3. Reflection Engine identifica falhas/correções/padrões.
4. Padrões repetidos viram Skill candidates.
5. Improvement Queue reúne mudanças sugeridas.
6. Aplicação/patch de código continua supervisionada.
