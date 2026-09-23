# Sind-AI — Personal Autonomy Roadmap

## Objetivo

Evoluir o Jarvis de um assistente local com ferramentas para um **agente operacional pessoal autônomo** que:

- entende o contexto atual do computador e dos projetos;
- observa como o usuário trabalha;
- aprende procedimentos por demonstração e por repetição;
- cria Skills reutilizáveis;
- procura documentação e aprende capacidades ausentes;
- executa tarefas simples e complexas de ponta a ponta;
- verifica o resultado antes de considerar uma tarefa concluída;
- pede demonstração humana somente quando não consegue aprender com segurança;
- preserva as capacidades atuais e permite evolução incremental.

A regra central de engenharia é: **nenhuma fase nova deve depender de substituir o core atual de uma vez**. As novas camadas entram por interfaces aditivas e feature flags/ativação explícita.

---

## Arquitetura-alvo

```text
Usuário / Gestor
       |
       v
Jarvis Supervisor
       |
       +-- Work Manager / projetos / backlog
       +-- Planner / Long Horizon
       +-- Context Engine
       +-- Personal Memory
       +-- Skill & Capability Resolver
       |
       v
Application Expert Router
       |
       +-- Photoshop Expert
       +-- VSCode Expert
       +-- Browser Expert
       +-- Git/GitHub Expert
       +-- Vercel Expert
       +-- SindPetshop Expert
       +-- Office/OBS/etc.
       |
       v
Execution Layer
       |
       +-- API / SDK / CLI
       +-- app bridge nativo
       +-- Windows UI Automation
       +-- browser DOM
       +-- vision + mouse/keyboard (fallback)
       |
       v
Verifier -> Experience -> Memory -> próxima execução melhor
```

Em paralelo:

```text
Observer -> Activity Ledger -> Trajectory Store -> Pattern Miner
                                              |
                                              v
                                  Procedural Learning
                                              |
                              Skill Candidate / Playbook
```

---

## Princípios de compatibilidade

1. **Preservar `JarvisAgent` como fachada** enquanto os novos subsistemas amadurecem.
2. **Não remover Actions/Workflows/Skills existentes.**
3. Novas Actions entram por catálogos suplementares (`actions/catalog.d/*.json`).
4. Persistência nova continua fora da pasta da release, em `~/JarvisData`.
5. Observação contínua é opt-in e pode ser desligada sem apagar histórico.
6. Aprendizado operacional não deve exigir fine-tuning a cada correção.
7. Modelos mais pesados são fallback, não requisito para observação contínua.
8. Toda capacidade nova precisa de um verificador de resultado antes de ganhar autonomia alta.

---

# Fase 1 — Personal Context Foundation (incluída neste patch)

### Entregue

- Activity Ledger em SQLite.
- observador passivo persistente de baixo custo;
- detecção do aplicativo/janela ativa;
- identificação inicial de Photoshop, VSCode, Visual Studio, browsers, Office, OBS, Explorer e terminais;
- `document_hint` derivado do título da janela;
- histórico recente de contexto;
- resumo de atividade;
- detecção simples de sequências repetidas de aplicativos;
- ponte `ingest_event()` para futuros plugins de aplicativos;
- suporte a eventos estruturados replayable dentro das demonstrações;
- catálogos de Actions suplementares sem editar o catálogo monolítico;
- comandos naturais para testar pela interface atual.

### Comandos de teste

```text
ative o aprendizado contínuo
status do observador pessoal
o que estou fazendo agora?
o que eu fiz nos últimos 30 minutos?
resuma minha atividade dos últimos 60 minutos
quais padrões de trabalho você percebeu?
desative o aprendizado contínuo
```

A observação explícita existente continua funcionando:

```text
Observe enquanto eu faço criar uma publicação
...
terminei a demonstração
```

### O que a Fase 1 NÃO faz ainda

- não grava vídeo da tela;
- não grava conteúdo digitado em background;
- não cria automações automaticamente a partir de padrões;
- não controla Photoshop por API;
- não usa VLM continuamente;
- não altera o core sozinho.

Isso é proposital: primeiro criamos a camada estável de contexto e eventos.

---

# Fase 2 — Trajectory Store + Procedural Memory

Transformar eventos isolados em **sessões de trabalho compreensíveis**.

Adicionar:

- início/fim automático de episódios de trabalho;
- agrupamento por projeto;
- sequências de ações, apps, arquivos e resultados;
- memória episódica;
- memória procedural;
- comparação entre várias demonstrações da mesma tarefa;
- parâmetros variáveis vs. passos constantes;
- score de confiança do procedimento;
- busca de trajetórias semelhantes.

Exemplo:

```text
trajetória A + trajetória B + trajetória C
                |
                v
"Criar post SindPetshop"
inputs: título, texto, imagem, nome_saida
procedimento: template -> conteúdo -> layout -> revisão -> export
```

---

# Fase 3 — Photoshop Bridge (prioridade alta)

Criar um plugin UXP `Jarvis Photoshop Bridge`.

O bridge deve publicar no `ObservationEngine.ingest_event()`:

- documento ativo;
- dimensões;
- árvore de layers;
- layer selecionada;
- eventos `actionJSON`/descritores;
- transformações;
- alterações de texto;
- exportações;
- estado antes/depois em checkpoints;
- opcionalmente thumbnails/screenshot do canvas.

Para execução, preferir:

1. UXP/Photoshop API;
2. `batchPlay`;
3. UI Automation;
4. visão + mouse como fallback.

O evento estruturado pode carregar um `replay`:

```json
{
  "source": "photoshop_uxp",
  "event_type": "app_action",
  "app_id": "photoshop",
  "payload": {"descriptor": "..."},
  "replay": {
    "tool": "photoshop.batch_play",
    "args": {"descriptor": "..."}
  }
}
```

Como a Fase 1 já entende `replay`, uma demonstração futura poderá compilar eventos do Photoshop diretamente em Skill.

---

# Fase 4 — Application Experts

Adicionar especialistas por domínio, sem transformar o modelo principal em especialista de tudo.

Cada Expert mantém:

- ferramentas disponíveis;
- documentação local/indexada;
- experiências;
- demonstrações;
- Skills;
- verificadores;
- estado atual do aplicativo.

Primeiros Experts:

- `PhotoshopExpert`
- `VSCodeExpert`
- `BrowserExpert`
- `GitExpert`
- `GitHubExpert`
- `VercelExpert`
- `SindPetshopExpert`

O Supervisor roteia tarefas para Experts e recebe resultados compactos.

---

# Fase 5 — Visual Memory + Correction Learning

Guardar pares:

```text
resultado gerado pelo Jarvis
        -> correção humana
        -> resultado final aprovado
```

Para design:

- imagem final;
- arquivo fonte/PSD quando disponível;
- estrutura de layers;
- tema;
- texto;
- dimensões;
- referência visual;
- alterações realizadas pelo usuário;
- avaliação final.

O objetivo é aprender não apenas ações, mas **critérios de decisão**.

Exemplos:

- onde posicionar texto quando há rosto na foto;
- quando reduzir texto antes de reduzir fonte;
- margens recorrentes;
- relação título/corpo;
- composição típica do MODO SIND;
- como o usuário corrige enquadramento.

---

# Fase 6 — Self Research / Capability Learner

Ao encontrar uma lacuna:

```text
não sei fazer
 -> procurar experiência semelhante
 -> procurar Skill/Action/Workflow existente
 -> pesquisar documentação oficial
 -> procurar API/SDK/CLI
 -> criar capability experimental
 -> testar em sandbox/cópia
 -> verificar resultado
 -> promover capacidade
 -> se falhar, pedir demonstração
```

A Capability Acquisition atual deve ser ampliada, não substituída.

Novos estados sugeridos:

```text
DISCOVERED
EXPERIMENTAL
LEARNED
VALIDATED
TRUSTED
AUTONOMOUS
```

---

# Fase 7 — Work Manager

O usuário deixa de comandar passo a passo e passa a definir objetivos.

Exemplo:

```text
"Cuide das redes do SindPetshop nesta semana."
```

O Jarvis cria backlog próprio:

- análise das métricas;
- escolha de temas;
- pesquisa;
- textos;
- imagens;
- Photoshop;
- exportação;
- revisão;
- publicação;
- acompanhamento;
- relatório.

Os Jobs do Long-Horizon são a base natural para isso.

---

# Fase 8 — Verification Everywhere

Nenhuma tarefa deve ser considerada concluída apenas porque não houve exception.

Exemplos:

### Photoshop

- arquivo existe;
- dimensões corretas;
- layers obrigatórias;
- texto não transborda;
- visual dentro do padrão esperado.

### Site

- build passa;
- deployment conclui;
- health check retorna sucesso;
- página alvo abre;
- elemento esperado existe.

### Git/GitHub

- diff esperado;
- testes passam;
- commit existe;
- push chegou ao remoto.

### Relatórios

- dados presentes;
- período correto;
- totais consistentes;
- arquivo exportado.

Resultado verificado alimenta Adaptive Experience.

---

# Fase 9 — Autonomy Manager

Autonomia deve ser conquistada por competência e evidência.

Cada Skill/Expert possui:

- execuções;
- sucessos;
- falhas;
- correções humanas;
- verificações;
- confiança;
- nível de autonomia.

Exemplo:

```text
SindPetshop.StaticPost
execuções: 64
sucesso verificado: 62
correções humanas: 3
confiança: 0.96
nível: AUTONOMOUS
```

Isso permite autonomia alta sem tratar todas as ações como equivalentes.

---

# Fase 10 — Computer-use visual fallback

Somente para interfaces sem API/bridge/UIA confiável:

- screenshot sob demanda;
- parser de UI;
- VLM local ou remoto opcional;
- grounding visual;
- mouse/teclado;
- verificação pós-ação.

No hardware CPU-first, visão contínua não deve ser a estratégia principal.

Hierarquia:

```text
API/SDK
 -> app bridge
 -> CLI
 -> UI Automation
 -> browser DOM
 -> visão + mouse/teclado
```

---

# Fase 11 — Background Proactivity

Eventos passam a iniciar raciocínio:

- deployment falhou;
- CI falhou;
- relatório está vencendo;
- publicação prevista não existe;
- métrica mudou;
- arquivo esperado chegou;
- comentário relevante apareceu.

O Jarvis avalia se deve:

- resolver;
- criar tarefa;
- pedir decisão;
- apenas informar.

---

# Fase 12 — Self Development supervisionado

O Jarvis pode propor e implementar melhorias no próprio repositório, mas por pipeline de engenharia:

```text
gap detectado
 -> branch
 -> alteração
 -> testes
 -> auditoria automática
 -> diff
 -> validação
 -> merge/deploy conforme política
```

Evitar edição silenciosa do core em produção.

---

## Métricas de evolução

As métricas mais importantes não são quantidade de Actions.

Medir:

1. `% de tarefas concluídas ponta a ponta sem intervenção`;
2. `% de resultados aprovados sem correção`;
3. `tempo humano economizado`;
4. `número de procedimentos ensinados apenas uma vez`;
5. `taxa de reaproveitamento de experiências`;
6. `taxa de aquisição autônoma de capacidades`;
7. `falhas detectadas pelo verifier antes de chegar ao usuário`;
8. `confiança por Skill/Expert`;
9. `custo de CPU/RAM por observação`;
10. `quantidade de interrupções desnecessárias ao usuário`.

A métrica-síntese do projeto deve ser:

> **Depois que um procedimento foi aprendido e validado, quantas vezes o usuário ainda precisa executá-lo manualmente?**

O alvo é aproximar esse número de zero.
