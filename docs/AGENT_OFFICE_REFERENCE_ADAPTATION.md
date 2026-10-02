# Agent Office → Jarvis HQ: adaptação de conceitos

O projeto de referência enviado pelo usuário é o **Agent Office**, da AgentSystemLabs, licenciado sob MIT.
Nesta base, não incorporamos o runtime nem os assets do projeto. Usamos a referência para validar conceitos de UX/observabilidade.

## Conceitos que entram no Jarvis

### 1. Agentes em estações reais
No Jarvis HQ, cada personagem/mesa representa um Agent Card ou worker real.
Nada trabalha visualmente sem status correspondente no backend.

### 2. “Needs you”
A referência destaca trabalhadores que estão esperando intervenção humana.
No Jarvis isso é tratado como `attention`: approvals pendentes, tasks bloqueadas ou futuras solicitações de input.

### 3. Estado visível
Estados iniciais do escritório:

- `planned`
- `idle`
- `working`
- `needs_input`
- `error`

A fonte de verdade permanece no Jarvis Core.

### 4. Projetos como espaços
A referência usa um andar por repositório. No Jarvis, a evolução prevista é um **Workspace/Floor por projeto**, porque nossos projetos não são apenas código.

### 5. Personagens não são processos
Uma mesa pode representar um agente disponível sem manter um modelo carregado.
O worker só existe enquanto há trabalho real.

### 6. HQ como observabilidade, não como cérebro
O escritório nunca cria verdade paralela. Ele é uma projeção do Event Bus, Task Engine, Agent Registry, Approvals e Artifacts.

## O que não copiamos

- gestão centrada em terminais/PTY;
- GitHub como núcleo de todos os projetos;
- minigames e mecânicas decorativas;
- Node como requisito do Core;
- runtime de agentes de código externos como arquitetura principal.

## Tecnologia nesta base

Para acelerar o produto sem adicionar Node/Three.js agora, a v0.3 inclui um HQ web leve, servido pelo próprio Python e atualizado por polling local.
Ele é uma implementação temporária do contrato visual.

No futuro podemos substituir o renderer por:

- Three.js/WebGPU;
- QML 2D/isométrico;
- engine própria;

sem mudar o backend, porque o contrato é `/api/hq` → `jarvis.hq.snapshot.v1`.

Se código ou assets do Agent Office forem reutilizados futuramente, a licença MIT e o aviso de copyright correspondente deverão ser preservados.
