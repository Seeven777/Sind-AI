# Jarvis HQ Protocol v1

Endpoint local atual:

`GET /api/hq`

Schema:

```text
jarvis.hq.snapshot.v1
```

Campos principais:

```text
core
  name
  status

office
  theme
  rooms[]

departments
  <department>[]
    id
    name
    status
    available
    task_id
    model
    mission

missions[]
attention[]
timeline[]
metrics
```

A UI não pode alterar o status de agentes diretamente.
Comandos futuros serão endpoints explícitos que passam por Policy/Approval/Task Engine.
