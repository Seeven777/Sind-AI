# Release Notes — Jarvis Personal GPT 1.9

## Adaptive Experience

Nova camada persistente de aprendizado por resultado real.

### Adicionado

- `experience/engine.py`;
- `experience/commands.py`;
- `cognitive/adaptive_experience.db`;
- perfis de competência;
- eventos de experiência;
- regras adaptativas por playbook;
- candidatos de adaptação;
- rollback de regras;
- retrospectiva de aprendizado;
- mapa de competências;
- feedback Útil/Não útil no Desktop;
- feedback Útil/Não útil no Mobile;
- associação de feedback ao pedido/playbook recente;
- janela temporal para evitar associar feedback a uma rotina antiga;
- ranking de playbooks influenciado por experiência;
- Swarm com ajuste fino de especialistas por desempenho;
- regras aprendidas dentro da execução Long-Horizon;
- criação de playbook a partir de Job;
- registro persistente de playbooks aprendidos;
- botão `Salvar como rotina` em Jobs concluídos;
- UI de adaptações supervisionadas;
- métricas de experiência no Centro de Controle e Mobile.

### Mantido

- 144 Workplace Playbooks nativos;
- 237 capabilities públicas;
- 611 Actions;
- 474 Workflows;
- 1322 recursos brokered;
- Institutional Workspace;
- Long-Horizon;
- Swarm;
- Apprenticeship;
- Capability Acquisition;
- Mobile Companion;
- AutoUpdater;
- execução sem timeout artificial.

### Segurança

A experiência não pode instalar código arbitrário silenciosamente. Mudanças estruturais são supervisionadas e ações externas continuam respeitando confirmações.
