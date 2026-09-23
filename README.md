# Jarvis Personal GPT 1.8 — Workplace Intelligence

Jarvis 1.8 mantém as camadas anteriores — Personal GPT, Swarm Intelligence, Apprenticeship, Capability Acquisition, Long-Horizon Autonomy e Institutional Workspace — e adiciona uma biblioteca operacional de **144 playbooks** para a rotina do SindPetshop-SP.

## O que muda

- 144 rotinas locais em 12 áreas;
- busca e recomendação de playbooks por linguagem natural;
- contexto automático de playbooks relevantes no prompt do Jarvis;
- preferência pelas abas institucionais já autenticadas;
- execução de playbooks como Jobs persistentes com checkpoints;
- ranking que aprende com uso e conclusão das rotinas;
- sugestões contextuais no Inspector;
- pesquisa/execução de playbooks pelo Centro de Controle;
- métricas do Workplace Intelligence no desktop e mobile;
- atalho de briefing diário;
- política `free/local-first` em toda a biblioteca.

Consulte `WORKPLACE_INTELLIGENCE.md` para a lista completa dos 144 playbooks.

## Política de custo

A 1.8 não adiciona dependências pagas. Os playbooks usam modelos locais, ferramentas do próprio Jarvis, abas institucionais, Knowledge Base, fontes públicas gratuitas e conectores já autorizados.

## Execução

Pedidos comuns continuam leves. O Jarvis consulta playbooks como contexto somente quando relevantes. A execução explícita de um playbook usa o Long-Horizon Runtime para poder criar checkpoints, pausar, retomar e sobreviver ao reinício.
