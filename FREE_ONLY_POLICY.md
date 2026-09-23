# Política FREE-ONLY — Jarvis Autonomous Operations 0.9

O núcleo do Jarvis deve funcionar sem assinatura, compra de créditos ou API paga.

## Permitido

- Python e bibliotecas open source;
- Ollama e modelos locais;
- SQLite/FTS5;
- Windows UI Automation;
- Playwright usando Edge/Chrome já instalado;
- APIs públicas realmente gratuitas;
- RSS/Atom;
- dados públicos;
- WordPress REST API do próprio site;
- integrações HTTPS pertencentes/autorizadas pela organização;
- keyring do sistema para credenciais;
- scheduler/monitores locais;
- Team Portal local.

## Não pode virar dependência obrigatória

- API cobrada por token;
- assinatura mensal;
- créditos comprados;
- cartão obrigatório;
- serviço cuja função principal deixa de operar sem pagamento.

## Connector Gateway

O gateway é infraestrutura. A existência do gateway não autoriza automaticamente
um serviço externo.

Antes de um connector profissional entrar no fluxo principal:

1. confirmar que o serviço é autorizado pelo usuário/organização;
2. confirmar HTTPS;
3. cadastrar somente os endpoints necessários;
4. usar princípio do menor privilégio;
5. manter o connector desabilitado até revisão;
6. classificar escrita/publicação como risco elevado;
7. manter segredos no keyring;
8. nunca persistir senha/token em logs, Skills ou prompts.

Se uma API profissional for paga, ela não pode ser necessária para o
funcionamento base do Jarvis. O usuário pode futuramente escolher conectar um
serviço já contratado pela própria organização, mas isso é um acesso opcional,
não parte da promessa gratuita do projeto.

## Autonomia

Autonomia não significa execução sem limites.

READ pode ser automatizado quando seguro.

WRITE/PUBLISH/ADMIN devem passar pelas regras de governança e, em execução
autônoma, por Approval Queue quando classificadas high/critical.

## Team Portal

Padrão: `127.0.0.1`.

A exposição em LAN (`0.0.0.0`) é opcional e só deve ocorrer após revisão de:
- firewall;
- senhas;
- coleções liberadas;
- roles;
- informações internas disponíveis.

## Hardware-alvo

- Ryzen 5 5600GT
- ~16 GB RAM
- Radeon integrada
- sem NVIDIA dedicada
- qwen3:4b em CPU
- contexto 4096

A inteligência deve continuar crescendo prioritariamente por software
determinístico, memória, conhecimento, ferramentas, automações e integrações,
não por exigir modelos cada vez maiores.


## Workplace Intelligence 1.8

Todos os 144 playbooks usam `free_only=true`. A camada não requer API paga, assinatura adicional ou modelo hospedado. Integrações externas continuam condicionadas às credenciais/serviços que a organização já possui; o playbook em si não adiciona custo.
