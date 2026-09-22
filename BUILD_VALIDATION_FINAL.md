# Validação — Jarvis Personal GPT 1.0 RC

## Aprovado no ambiente de build

- Python compileall: OK
- JavaScript syntax: OK
- `personal_gpt_test.py`: OK
- `self_test.py`: OK
- `foundation_regression_test.py`: OK
- `institutional_test.py`: OK
- `autonomous_operations_test.py`: OK
- `cognitive_test.py`: OK
- `catalog_routing_test.py`: OK
- `team_portal_test.py`: OK

## Cobertura do teste Personal GPT

- projetos persistentes;
- notas de projeto;
- anexos -> Knowledge Base;
- recuperação de anexo;
- Learning Journal;
- Reflection Engine;
- Skill candidate após repetição;
- falha -> reflection;
- Improvement Queue;
- resolução de serviços institucionais;
- Fast Path de Slack;
- Context Orchestrator;
- Hardware Profiler.

## Dependências do Windows

Devem ser testadas no PC de referência após `install.bat`:
- pywinauto / UI Automation;
- Browser Agent real;
- Ollama real;
- disponibilidade dos modelos;
- sessões autenticadas;
- connectors profissionais;
- WordPress real.

`routing_regression_test.py` não roda no ambiente Linux de build por depender de `pywinauto`; no Windows ele deve ser executado normalmente.
