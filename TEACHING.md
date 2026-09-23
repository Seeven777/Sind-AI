# Ensinar o Jarvis

A 1.5 adiciona dois modos complementares de ensino.

## 1. Ensino por explicação

Exemplo:

`Quero te ensinar como fazer uma homologação interna`

O Jarvis entra em modo de ensino. As mensagens seguintes viram anotações da rotina.

Quando terminar:

`finalizar ensino`

O conteúdo é compilado em um procedimento persistente. Em pedidos semelhantes, o procedimento é recuperado automaticamente e entra no contexto operacional.

Comandos úteis:

- `vou te ensinar como ...`
- `quero te ensinar ...`
- `aprenda comigo ...`
- `finalizar ensino`
- `cancelar ensino`
- `o que eu te ensinei?`

Os procedimentos ficam em `~/JarvisData/cognitive/apprenticeship.db`.

## 2. Ensino por demonstração

Exemplo:

`Observe enquanto eu faço cadastrar um atendimento`

O Jarvis ativa o Observation Engine. Faça a rotina no Windows normalmente.

Quando terminar:

`terminei a demonstração`

A demonstração é convertida em uma Skill executável.

Por privacidade, o conteúdo digitado durante a demonstração **não é armazenado**. Ele vira uma entrada variável da Skill.

Exemplo de uso futuro:

`Faça o cadastro de atendimento como eu te ensinei.`

O Agent Runtime pode recuperar a Skill relevante e executá-la usando as ferramentas existentes, ainda respeitando confirmações e permissões.

## Aprendizado de uso

Procedimentos textuais acumulam `uses`, `successes` e confiança. Uso bem-sucedido aumenta a confiança; falhas reduzem a confiança para que uma rotina problemática não seja tratada como verdade perfeita indefinidamente.

Isso não retreina o modelo base. O aprendizado é persistente e auditável.
