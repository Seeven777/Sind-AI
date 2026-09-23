# Jarvis Swarm Intelligence

A versão 1.5 introduz coordenação multiagente local sem mudar a experiência principal: o usuário continua falando com um único Jarvis.

## Ideia

Tarefas simples continuam usando Fast Path ou conversa leve.

Tarefas complexas podem ser decompostas internamente em papéis especializados:

- Planner — decompõe o objetivo e define critérios de conclusão;
- Researcher — define evidências/fontes necessárias;
- Institutional — aplica contexto SindPetshop-SP/CCTs/conhecimento interno;
- Operator — organiza ações de desktop/browser/arquivos;
- Analyst — define métricas e leituras de dados;
- Content — estrutura comunicação/campanhas;
- Developer — orienta código, site, integrações e rollback;
- Reviewer — revisa a entrega final.

## Hardware

No hardware atual, os especialistas são executados **sequencialmente**. Isso evita abrir várias cópias pesadas do modelo ao mesmo tempo.

A arquitetura combina dois níveis já instalados:

- FAST model para Planner/especialistas/revisão;
- REASON model para síntese/execução difícil.

Se outros modelos locais forem instalados futuramente, o pool pode ser ampliado sem alterar a interface.

## Blackboard

Cada coordenação possui um Blackboard persistente em `~/JarvisData/cognitive/swarm_blackboard.db`.

Ele registra:

- objetivo;
- plano;
- orientações dos especialistas;
- procedimentos ensinados utilizados;
- resultado;
- revisão.

O Blackboard é infraestrutura interna. O chat mostra apenas estágios úteis como `Definindo estratégia`, `Consultando especialista` e `Revisando entrega`.

## Segurança

Swarm não remove governança. Agentes podem propor ações, mas high/critical continuam exigindo as confirmações já implementadas.

O Swarm não cria permissões que o usuário não concedeu e não inventa acessos.
