# Agent Mode Presence v4

## Objetivo
Corrigir a presença cotidiana do Jarvis sem ampliar artificialmente a superfície do produto: voz confiável, contexto pessoal conectado, Core mais legível, Office coerente e atividade multiagente verdadeira.

## Alterações

- Gmail e Google Calendar agora são sincronizados antes de respostas de briefing, inbox e pedidos pessoais relacionados a compromissos/e-mails.
- O prompt do Jarvis não contém mais a afirmação obsoleta de que Inbox/e-mail estão desconectados; o estado real dos conectores é injetado no contexto, inclusive em modo deep.
- O roteamento de intenção reconhece pedidos combinados de e-mail + calendário como briefing pessoal.
- Briefing mostra fontes saudáveis, eventos próximos e itens recentes sincronizados, sem inventar dados.
- Voz ganhou fallback nativo Windows SAPI além de ElevenLabs, Piper e Web Speech; a Home tenta manter respostas faladas habilitadas.
- O Core principal recebeu núcleo luminoso, plasma/halo interno, órbitas discretas, maior legibilidade e resposta mais evidente ao ponteiro/estado.
- No Office, agentes são posicionados nos assentos reais das estações, em vez de coordenadas decorativas independentes; avatares e estações foram refinados.
- Ciclo autônomo de agentes agora executa pares independentes concorrentemente quando isso é verdadeiro (Inbox+Memory, Analyst+Operator read-only, Creator+Developer), preservando Reviewer como etapa posterior.
- Falha de um papel não é usada para fingir atividade dos demais.

## Validação

- `pytest -q`: 102 testes aprovados.
- `scripts/release_self_test.py`: todos os checks aprovados.
- Python e JavaScript alterados passaram por checagem de sintaxe.

A renderização final no Windows deve ser validada no ambiente do usuário, pois o Chromium do ambiente de construção bloqueia URLs locais por política administrativa.
