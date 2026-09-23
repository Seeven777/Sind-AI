# Jarvis Personal GPT 1.9 — Adaptive Experience

Jarvis 1.9 mantém as camadas anteriores — Personal GPT, Swarm Intelligence, Apprenticeship, Capability Acquisition, Long-Horizon Autonomy, Institutional Workspace e Workplace Intelligence — e adiciona uma camada de **experiência adaptativa persistente**.

A mudança principal é simples: o Jarvis não deve apenas lembrar que algo aconteceu. Ele deve alterar a forma como tenta executar tarefas semelhantes depois.

## O que muda

- feedback explícito `funcionou / não funcionou / da próxima vez` vira experiência operacional;
- respostas do Desktop e Mobile possuem feedback **Útil / Não útil**;
- sucesso e falha de playbooks atualizam uma confiança observada;
- falhas repetidas geram candidatos de adaptação supervisionados;
- correções textuais explícitas podem virar regras seguras imediatamente;
- cada playbook pode receber regras aprendidas sem alterar o catálogo nativo;
- regras aprendidas entram de fato nos checkpoints do Long-Horizon;
- ranking de playbooks considera desempenho histórico;
- o Swarm aprende quais especialistas apresentam melhores resultados e usa isso como ajuste fino;
- Jobs concluídos podem virar novos playbooks locais persistentes;
- playbooks aprendidos são salvos em `JarvisData`, fora da pasta da release;
- adaptações podem ser aprovadas, rejeitadas ou revertidas;
- mapa de competências mostra usos, sucessos, falhas, correções e confiança;
- retrospectiva de aprendizado mostra onde o Jarvis melhorou e onde ainda precisa de supervisão.

## Ciclo de experiência

```text
pedido
  ↓
playbook / swarm / ferramentas
  ↓
execução
  ↓
resultado real
  ↓
feedback + evidência
  ↓
Adaptive Experience
  ├─ confiança
  ├─ regra aprendida
  ├─ adaptação proposta
  └─ nova rotina reutilizável
  ↓
próxima execução diferente
```

## Comandos úteis

```text
Isso funcionou.

Isso não funcionou.

Da próxima vez, use o dashboard antes de pesquisar na web.

Faça uma retrospectiva de aprendizado.

Mostre o mapa de competências.

Liste adaptações.

Aprove a adaptação #3.

Rejeite a adaptação #3.

Reverta a última adaptação.

Transforme o job #17 em uma rotina.
```

## Persistência

A nova camada usa:

```text
~/JarvisData/cognitive/adaptive_experience.db
~/JarvisData/workplace/custom_playbooks.json
```

Esses arquivos ficam fora da pasta da versão e sobrevivem a atualizações do Jarvis.

## Segurança

O Adaptive Experience não reescreve silenciosamente o código do Jarvis.

Correções de linguagem/instrução podem virar regras de prompt porque não instalam executáveis nem pulam confirmações. Alterações estruturais ficam como candidatos supervisionados.

Ações externas continuam sujeitas à governança existente.

## Política de custo

A 1.9 continua **local-first e free-only**. Nenhum serviço pago foi adicionado como requisito.
