# Adaptive Experience — Jarvis 1.9

## Objetivo

Transformar uso real em melhoria operacional persistente sem depender de retreino de pesos, serviços pagos ou autoedição insegura de código.

## Estruturas persistentes

### Experience Events
Registra sucessos, falhas, correções, avaliações e resultados de Jobs.

### Competence Profiles
Mantém perfil por:
- playbook;
- categoria;
- agente do Swarm.

Cada perfil acompanha:
- usos;
- sucessos;
- falhas;
- correções;
- confiança;
- sequências recentes de sucesso/falha.

### Playbook Rules
Correções e aprendizados específicos de uma rotina.

As regras são aplicadas ao prompt de execução de cada checkpoint do Long-Horizon.

### Adaptation Candidates
Mudanças sugeridas por experiência que aguardam aprovação quando não são uma correção textual segura.

### Playbook Evolution
Registra a origem de rotinas criadas a partir de Jobs executados.

## Feedback

O Jarvis reconhece linguagem natural como:

- `isso funcionou`;
- `isso não funcionou`;
- `da próxima vez ...`;
- `prefiro ...`;
- `evite ...`;
- `não faça ...`.

O Desktop e Mobile também possuem botões **Útil** e **Não útil**.

## Swarm adaptativo

O Swarm continua escolhendo especialistas por relevância semântica. A experiência não substitui esse roteamento.

Ela funciona como ajuste fino de ranking entre candidatos já considerados relevantes.

Assim:
- um agente historicamente bem-sucedido ganha pequeno bônus;
- falhas repetidas reduzem esse bônus;
- a pertinência ao objetivo continua dominante.

## Criação de rotinas por execução

Um Job com checkpoints pode ser convertido em playbook:

`Transforme o job #12 em uma rotina.`

O novo playbook é salvo em:

`JarvisData/workplace/custom_playbooks.json`

e carregado junto dos 144 playbooks nativos.

## Rollback

Toda regra adaptativa pode ser desativada.

Comando natural:

`Reverta a última adaptação.`

Isso permite experimentar e corrigir o próprio aprendizado sem mexer no código da aplicação.
