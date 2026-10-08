# Jarvis Agent Mode v12 — Morning Presence

## Objetivo
Transformar a primeira abertura do dia em um ritual real de presença: iniciar, verificar infraestrutura, acordar visualmente, falar apenas o essencial e materializar informações em gadgets temporários.

## Fluxo matinal
1. Boot cinematográfico com verificação visual de runtime, memória, modelos, conectores e voz.
2. Wake animation do Jarvis Core.
3. Cumprimento curto.
4. Gadget meteorológico estruturado e animado, com resumo falado + dados visuais + próximas horas.
5. Transição de saída do clima e materialização de até 8 cards de notícias clicáveis com fonte.
6. Transição para responsabilidades do dia vindas do organizador de marketing conectado.
7. Melhorias pendentes são mencionadas de forma curta quando existirem.
8. Jarvis encerra perguntando: “O que faremos hoje?” e devolve foco ao campo de comando.

## Weather
- `weather.forecast` agora também retorna previsão horária estruturada.
- O briefing autônomo usa a ferramenta meteorológica antes de qualquer fallback textual.
- Temperatura, sensação, umidade, chuva, vento, máxima/mínima e próximas horas ficam disponíveis ao gadget sem depender de interpretação do LLM.

## News
- O briefing preserva URL e identidade da fonte em cada destaque.
- Até 7/8 destaques podem ser materializados como cards independentes e clicáveis durante a sequência.

## Organizador de tarefas
- Novo conector read-only `marketing.tasks` para `https://mkl-sind-petshop-sp.vercel.app`.
- Usa Playwright e sessão autenticada persistente.
- Observa respostas JSON da aplicação (inclusive APIs REST/Supabase quando presentes) e possui fallback para cards visíveis.
- Tarefas concluídas são filtradas; pendências são priorizadas e exibidas no briefing.
- Credenciais nunca são gravadas no código. `Connect-Marketing-Tasks.cmd` armazena os segredos localmente via Windows DPAPI e mantém o estado autenticado do navegador.

## Desktop + mobile
- A mesma sequência existe no Companion e no Mobile.
- Briefing executa automaticamente apenas na primeira abertura matinal do dispositivo naquele dia.
- “Briefing do dia” permite reproduzir a sequência manualmente.
- É possível encerrar o ritual a qualquer momento.

## Segurança
- A integração do organizador é somente leitura.
- Nenhuma credencial do usuário é incluída nos ZIPs.
- Gadgets continuam sendo renderizadores controlados; não executam HTML arbitrário vindo do modelo.

## Validação
- 143/143 testes Python aprovados.
- `compileall` aprovado.
- Todos os JavaScripts do HQ passaram por `node --check`.
