# Jarvis Cognitive Runtime 1.0b

## Problema corrigido

Perguntas conversacionais simples, como:

`quem é o sindpetshop-sp?`

ainda passavam pelo Agent Runtime e pelo `qwen3:4b`. No hardware de testes isso podia atingir o timeout de 40 segundos.

## Nova arquitetura de modelos

- FAST: `qwen3:1.7b`
  - conversa;
  - perguntas curtas;
  - síntese pequena;
  - respostas fundamentadas.

- REASON: `qwen3:4b`
  - tool calling;
  - tarefas multi-etapas;
  - planejamento;
  - análise mais pesada.

O Jarvis escolhe o modelo conforme a tarefa.

## Conversation Runtime

Conversa comum não cria mais uma tarefa no Task Runtime.

Fluxo:

conversa → contexto recente/relevante → FAST model → resposta

Perguntas institucionais:

pergunta → perfil/base institucional → evidências internas →
fallback público oficial → FAST model → resposta

Se o modelo local ainda for lento, Jarvis retorna uma resposta determinística
baseada nas evidências em vez de apresentar um erro de timeout.

## Instalação

Depois de `install.bat`, execute uma vez:

`install_fast_model.bat`

Isso instala `qwen3:1.7b`.

O modelo principal `qwen3:4b` continua sendo usado para raciocínio e ferramentas.

## Resultado esperado para o caso reportado

`quem é o sindpetshop-sp?`

deve:
1. consultar conhecimento institucional local;
2. se estiver vazio, consultar fontes públicas do site oficial;
3. responder usando o modelo FAST;
4. se o FAST não responder no prazo, retornar a evidência pública diretamente;
5. nunca terminar apenas com o erro de timeout de 40s.
