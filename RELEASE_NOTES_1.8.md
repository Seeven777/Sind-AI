# Jarvis Personal GPT 1.8 — Workplace Intelligence

A 1.8 adiciona **144 novas rotinas operacionais reais** ao Jarvis, todas gratuitas/local-first, e transforma o conhecimento das rotinas do SindPetshop-SP em uma camada reutilizável pelo agente.

## 144 novas rotinas

São 12 playbooks em cada uma de 12 áreas:

- conteúdo;
- analytics;
- plataformas sociais;
- site/WordPress;
- pesquisa;
- CCT/institucional;
- campanhas;
- equipe/onboarding;
- operações;
- documentos/dados;
- automação/monitoramento;
- qualidade/governança.

A lista integral está em `WORKPLACE_INTELLIGENCE.md`.

## Melhorias de runtime adicionadas junto aos 144 playbooks

- Playbook Engine local;
- banco persistente de uso/aprendizado dos playbooks;
- busca semântica leve por nome, descrição, palavras-chave, serviço e agente;
- ranking adaptativo baseado em rotinas concluídas;
- contexto automático dos playbooks relevantes no System Prompt;
- preabertura controlada das abas institucionais corretas;
- limite de duas abas preabertas por tarefa para preservar RAM/CPU;
- compilação de playbook em plano operacional;
- execução como Long-Horizon Job com checkpoints;
- recuperação de resultado de playbook para melhorar ranking futuro;
- comandos naturais `Liste playbooks`, `Qual playbook para ...`, `Use o playbook ...`;
- tools `search_workplace_playbooks`, `run_workplace_playbook` e `workplace_stats`;
- sugestões de próximas rotinas no Inspector;
- busca de playbooks no Centro de Controle;
- início de playbook com um clique;
- métrica `PLAYBOOKS` no Centro de Controle;
- Self Awareness passa a conhecer a biblioteca real;
- briefing diário na tela inicial;
- métricas de playbooks e jobs no Mobile Companion;
- política `free_only=true` validada em todos os 144 itens.

## Como o Jarvis muda

Antes, uma tarefa como “faça a análise semanal das redes” precisava ser planejada praticamente do zero pelo modelo.

Agora o Jarvis pode recuperar `workplace.analytics.weekly_summary`, abrir primeiro o Insights institucional, usar o Analyst/Reviewer, seguir checkpoints já definidos e registrar se a rotina funcionou.

Os playbooks não substituem o raciocínio do modelo: reduzem improvisação, chamadas desnecessárias ao Qwen e uso errado de Google quando uma ferramenta institucional já existe.

## Hardware

A arquitetura continua voltada ao PC de referência CPU-first. O registry é JSON e o search é determinístico; nenhum modelo adicional fica carregado apenas para os playbooks. Sites institucionais continuam lazy-load e no máximo duas abas são preabertas automaticamente por execução.

## Custo

Nenhuma dependência paga foi adicionada. A biblioteca opera sobre modelos locais, ferramentas já instaladas, Knowledge Base, dados públicos gratuitos e sessões institucionais autorizadas.
