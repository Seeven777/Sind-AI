# Jarvis Cognitive Foundation 1.0a

Esta release muda a métrica do projeto. O objetivo não é aumentar o número de botões, Actions ou Workflows; é melhorar a capacidade de conversar, lembrar, pesquisar e decidir quando agir.

## Novo

- Conversation Store persistente entre reinicializações;
- recuperação FTS5 de conversas anteriores;
- Learning Journal com episódios e lições explícitas;
- memória semântica local opcional via Ollama embeddings;
- Public Data Registry/Broker com 28 fontes iniciais;
- descoberta de OpenAPI/Swagger/RSS/Sitemap;
- adapters diretos para fontes selecionadas, incluindo IBGE, Câmara, Dados.gov.br e Dados Abertos SP;
- contexto do Qwen reduzido;
- ferramentas enviadas ao modelo somente quando plausíveis;
- interface reconstruída como workspace de conversa;
- módulos técnicos removidos da navegação principal;
- Centro de Controle para diagnóstico/infraestrutura avançada;
- painel lateral reduzido a Contexto, Fontes e Atividade.

## Mantido no backend

Actions, Workflows, Skills, automações, monitores, approvals, Browser Agent, WordPress, Connectors, Team Portal, Research Engine e demais componentes da 0.9.1 continuam disponíveis. Eles deixaram de ser o centro da experiência.
