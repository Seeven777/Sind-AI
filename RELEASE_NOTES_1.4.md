# Jarvis Personal GPT 1.4 — Long-Running Runtime

Esta versão remove o limite artificial de tempo que interrompia o modelo local durante tarefas demoradas.

## Mudança principal

Antes:

`qwen3:4b ultrapassou 40s nesta etapa.`

Agora, por padrão:

- `agent_llm_timeout_seconds = 0`
- `agent_total_timeout_seconds = 0`
- `fast_model_timeout_seconds = 0`
- `research_llm_timeout_seconds = 0`

`0` significa: **não interromper automaticamente por tempo**.

## Progresso visível

Enquanto uma tarefa estiver ativa, a interface emite heartbeat contínuo, por exemplo:

`Pensando com qwen3:4b • ciclo 1/6 • 1m 18s • em andamento`

ou:

`Agente executando: browser.open • 2m 03s • em andamento`

O usuário continua vendo:

- estágio atual;
- modelo em uso;
- ciclo do agente;
- tempo decorrido;
- botão **Parar**.

## Limites que continuam existindo

Foram mantidos limites estruturais para impedir loops de autonomia sem fim:

- máximo de ciclos do Agent Runtime;
- máximo de tool calls por execução;
- confirmações para ações sensíveis;
- timeouts de rede/HTTP de ferramentas específicas quando tecnicamente necessários.

Esses limites não interrompem um modelo apenas porque demorou 40 segundos.

## Hardware

Em CPU, respostas complexas podem levar vários minutos. Esta release trata isso como execução válida, e não como erro.
