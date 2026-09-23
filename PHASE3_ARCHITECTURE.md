# Fase 3 — Self-Research + Verified Execution

O teste do WhatsApp falhou: a mensagem exibida foi enviada manualmente pelo usuário.

A lacuna encontrada é estrutural. O Capability Acquisition atual pesquisa
documentação, mas documentação é cadastrada como candidato informacional e não é
convertida em executor.

Esta fase acrescenta:

- SelfResearchLearner;
- coleta de evidências pelo ResearchEngine já existente;
- síntese restrita para Skills de GUI;
- lista fechada de ferramentas permitidas;
- proibição de código/shell vindo da web;
- persistência das fontes usadas;
- comandos naturais "pesquise como ... e tente ...";
- tentativa automática quando explicitamente pedida;
- separação entre "execução terminou sem exception" e "efeito externo verificado".

Próxima etapa:
pesquisa -> estratégia A -> executar -> observar estado -> verificar -> se falhar,
estratégia B -> verificar -> registrar qual abordagem funcionou.
