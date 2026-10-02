# Jarvis Next — v0.4.1 Runtime Unificado

## Correção principal

Companion e Jarvis HQ não criam mais runtimes concorrentes.

A porta local `127.0.0.1:4760` representa a única instância de UI + Product Runtime:

- `/` → Companion
- `/hq` → Jarvis HQ
- `/api/ping` → liveness barato, sem consultar modelo
- `/api/hq` → projeção do escritório
- `/api/briefing` → briefing
- `/api/chat` → Jarvis
- `/api/mission/team` → pipeline multiagente

`Start-Jarvis.cmd` e `Start-Jarvis-HQ.cmd` primeiro procuram a instância existente. Se ela existir, apenas abrem a página correspondente.

Se encontrarem uma instância antiga do Jarvis mantendo `instance.lock` mas sem servidor UI, o launcher valida que o PID pertence ao Jarvis, encerra somente essa instância legada e sobe o runtime unificado.

O single-instance lock continua obrigatório: ele agora protege o Core, e não impede múltiplas superfícies de visualização.
