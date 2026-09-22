# Diagnóstico de estabilidade — 0.7.3

## Problemas observados na 0.7.2

1. A pesquisa conseguia encontrar fontes, mas os resultados do Bing eram salvos como redirects `bing.com/ck`.
2. O qwen3:4b ainda recebia evidência excessiva e podia ultrapassar o timeout.
3. O fallback preservava snippets, mas não entregava síntese estruturada suficiente.
4. Tarefas antigas podiam continuar marcadas como RUNNING após reinício.
5. Não havia uma camada única para diagnosticar Ollama, rede, armazenamento, catálogos e tarefas.

## Respostas implementadas

- Source Resolver para decodificar redirects e limpar tracking.
- Ranking de fontes por autoridade e relevância.
- Extração HTML/PDF e evidence cards.
- Contexto de síntese reduzido para cerca de 3600 caracteres.
- Fallback determinístico com evidências, não apenas resultados do buscador.
- Heartbeat/status/attempts/last_error em tarefas.
- Reconciliação de tarefas órfãs no startup.
- Runtime Supervisor e tela Saúde.
- Document Intelligence e Workspace Intelligence para reduzir dependência do LLM.

## Princípio desta fase

O modelo local não deve carregar sozinho a inteligência do produto. O Jarvis deve resolver deterministicamente tudo que puder medir, extrair, verificar ou estruturar, reservando o qwen3:4b para decisão, síntese e linguagem.
