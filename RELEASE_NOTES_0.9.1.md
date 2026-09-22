# Release Notes — Jarvis Reliability Router 0.9.1

Esta é uma correção de confiabilidade sobre a 0.9, não uma expansão artificial do catálogo.

## Problema confirmado em teste real

`Procure workflows para monitorar um site.` caía no Ollama e atingia o timeout porque o parser aceitava apenas `workflow` no singular.

Também havia um problema relacionado:
- `Mostre os workflows relacionados ao assistente da equipe.` era interpretado como pedido de estatísticas;
- `Mostre as ações relacionadas à fila de aprovações.` também podia virar estatísticas;
- cumprimentos simples como `Olá` ainda podiam gastar o orçamento do modelo local.

## Correções

- `workflow` e `workflows`;
- buscas com `para`, `sobre`, `relacionados a/ao/à`, `disponíveis para`;
- comandos de estatísticas agora precisam ser pedidos exatos;
- ações receberam o mesmo tratamento;
- cumprimento simples virou Fast Path;
- busca de Action/Workflow Hub ganhou normalização de acentos;
- palavras irrelevantes são removidas do ranking;
- sinônimos operacionais ajudam buscas como:
  - automação → scheduler/automation;
  - monitorar → monitor/watch;
  - integração → connector/API;
  - usuários/permissões → user/grant/role;
  - aprovações → approval/governance;
  - lacunas → gap/knowledge.

## Objetivo

Pedidos de descoberta de ações/workflows não devem depender do qwen3:4b. O modelo local fica reservado para raciocínio e síntese, não para interpretar comandos determinísticos de catálogo.
