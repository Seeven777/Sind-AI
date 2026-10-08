# Agent Mode v9 — Performance Pass

A v9 transforma velocidade em uma métrica de produto, não apenas em uma otimização pontual.

## Resposta percebida

- Streaming real no Companion e no Mobile via `/api/chat/stream`.
- A primeira parte da resposta aparece assim que o modelo começa a gerar, sem esperar a resposta completa.
- Status transitórios mostram quando Jarvis está pesquisando, desenvolvendo ou raciocinando.
- Histórico enviado ao modelo agora é limitado por quantidade e tamanho para conversas longas não degradarem indefinidamente.

## Modelos

- Ollama usa `keep_alive=30m` para evitar descarregar o modelo entre interações.
- O modelo principal é aquecido em background durante o boot.
- Modo FAST continua disponível e o roteamento automático usa modelo rápido somente em interações triviais; tarefas substantivas preservam o modelo principal.

## Prioridade para o usuário

- Uma interação ativa passa a ter prioridade sobre o ciclo autônomo de background.
- Curiosidade/agentes autônomos cedem CPU enquanto o usuário conversa com Jarvis e retomam depois.
- Sincronização de Gmail/Calendar sai do caminho crítico do startup e ocorre em background.

## Interface

- Assets estáticos usam ETag, cache HTTP e gzip.
- Service Worker v9 mantém o shell estático quente sem armazenar APIs dinâmicas.
- Companion e Mobile agrupam atualizações de streaming por frame para reduzir renderizações.
- Polling fica mais lento/pausa quando a aba não está visível.
- Office adapta FPS, DPR, sombras e intervalo de sincronização conforme atividade e hardware.

## Observabilidade

- Novo `PerformanceMonitor` mede TTFT (tempo até o primeiro token) e tempo total.
- `/api/performance` expõe mediana/p95 das amostras recentes.
- Tela Sistema mostra TTFT, tempo total e número de amostras.
- Jarvis recebe contexto resumido da própria latência para detectar regressões futuras.

## Compatibilidade

- `/api/chat` antigo permanece disponível.
- Jarvis Anywhere/ngrok da v8 permanece inalterado.
- Segurança, aprovações e verificação operacional não foram relaxadas para ganhar velocidade.
