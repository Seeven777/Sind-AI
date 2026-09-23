# Build Validation — Jarvis Personal GPT 1.8

## Workplace Intelligence

Validado por `workplace_intelligence_test.py`:

- exatamente 144 novos playbooks;
- 12 categorias;
- 12 playbooks por categoria;
- IDs únicos;
- 100% `free_only`;
- todos com plano/checkpoints e agentes;
- busca de analytics, CCT e onboarding;
- contexto automático;
- execução via Long-Horizon;
- preabertura de serviços institucionais;
- persistência de uso;
- aprendizado por resultado;
- parser de comandos naturais;
- integração com Agent Runtime;
- bridge desktop;
- Control Center;
- sugestões no Inspector;
- início com um clique.

## Regressões executadas

Passaram novamente:

- Long-Horizon Autonomy;
- Institutional Workspace;
- Capability Acquisition;
- Swarm + Apprenticeship;
- Long-Running Runtime;
- UX Stability;
- Personal GPT;
- Cognitive Foundation;
- Self Awareness;
- Foundation Regression;
- Self Test.

O catálogo anterior permanece com:

- 237 capabilities públicas;
- 611 Actions;
- 474 Workflows;
- 1322 recursos brokered;

além dos 144 playbooks do Workplace Intelligence.

## Frontend / deploy

- `python -m compileall`: OK;
- `ui/web/app.js`: Node syntax OK;
- `mobile/web/app.js`: Node syntax OK;
- `vercel_portal/app.js`: Node syntax OK;
- `npm run build`: OK.

O build Vercel permanece como launcher estático; o runtime local continua no computador do usuário.
