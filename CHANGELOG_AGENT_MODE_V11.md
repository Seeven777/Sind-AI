# Jarvis Agent Mode v11 — Generative Surface Engine

## Objetivo
Fazer o Jarvis materializar interface contextual em vez de depender apenas de texto.

## Novo comportamento
- perguntas sobre clima geram um gadget compacto com métricas, resumo e fontes;
- pedidos de notícias geram um painel expansível com manchetes e links das fontes;
- pesquisas complexas materializam síntese, pontos-chave e evidências;
- agenda, inbox, agentes, sistema, comparação e análise de dados possuem superfícies próprias;
- a superfície nasce visualmente ao lado do Core, que reage no momento da materialização;
- o gadget começa compacto e pode ser expandido/recolhido;
- somente uma superfície principal permanece aberta, preservando a Home limpa;
- respostas com gadget usam uma fala resumida, evitando que Jarvis leia relatórios inteiros;
- a resposta textual continua disponível como fallback, mas fica visualmente secundária;
- a última superfície fica associada à conversa e reaparece ao reabrir o histórico;
- desktop e mobile usam o mesmo schema e o mesmo Surface Engine.

## Segurança
O LLM não injeta HTML. O backend produz apenas um schema estruturado e a UI renderiza somente componentes previamente registrados.
URLs exibidas nas fontes passam por validação HTTP/HTTPS no cliente e o backend elimina dados desnecessários das fontes.

## Arquitetura
`GenerativeSurfaceService` converte intenção + resposta + evidências em descritores `schema_version=1`.
`surface-engine.js` atua como registro de renderizadores confiáveis e gerencia materialização, expansão e ciclo de vida.

## Validação
- 135 testes automatizados passando;
- release self-test passando;
- Python compile check passando;
- JavaScript syntax check passando.
