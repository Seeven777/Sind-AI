# Build Validation — Jarvis Reliability Router 0.9.1

## Falha real reproduzida conceitualmente

No teste do Windows, o pedido:

`Procure workflows para monitorar um site.`

atingiu o timeout de 40s do modelo local.

Causa identificada no código:
- o parser aceitava `workflow` no singular;
- `workflows` no plural não correspondia ao Fast/Explicit Router;
- a frase caía no Agent Runtime/Qwen desnecessariamente.

## Correções verificadas offline

- Python compileall: OK
- Parser de workflows no plural: OK
- `Procure workflows para monitorar um site.` → search: OK
- `Mostre os workflows relacionados ao assistente da equipe.` → search: OK
- comando exato `Mostre os workflows.` → stats: OK
- `Mostre as ações relacionadas à fila de aprovações.` → search: OK
- `Mostre as ações disponíveis para administrar usuários e permissões...` → search: OK
- ranking de workflows de monitoramento: OK
- ranking de workflows do assistente da equipe: OK
- ranking de ações de aprovação: OK
- ranking de ações de equipe/permissões: OK
- cumprimento `Olá` recebeu Fast Path determinístico no código

## Teste completo do Agent Runtime

O ambiente de empacotamento atual não possui `pywinauto`, portanto
`routing_regression_test.py` não pode inicializar o `JarvisAgent` completo aqui.

Isso é esperado: esse teste depende da stack Windows usada pelo Jarvis.

No computador de testes, após `install.bat`, rode:

`run_routing_test.bat`

A versão 0.9.1 inclui no teste todos os comandos que falharam ou que foram
solicitados nesta rodada. O teste substitui o Ollama por uma função que gera
erro imediatamente. Portanto, se qualquer um desses comandos tentar chamar o
modelo local, o teste falhará de forma explícita em vez de esperar 40 segundos.

## Filosofia desta hotfix

Esta release não adiciona centenas de funções artificiais. Ela reduz a
dependência do Qwen para tarefas determinísticas de catálogo, porque a base
precisa ser confiável antes da próxima expansão institucional.
