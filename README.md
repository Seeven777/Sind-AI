# Jarvis Cognitive Runtime 1.0b

# Jarvis Cognitive Foundation 1.0a

Jarvis é um **GPT pessoal local**: conversa, mantém contexto, aprende preferências/correções, pesquisa dados públicos, usa bases locais e aciona ferramentas quando necessário.

O objetivo não é obrigar o usuário a escolher Actions, Workflows ou APIs. Esses componentes são infraestrutura secundária.

## Mudança visual

A interface principal agora contém apenas:

- histórico de conversas;
- chat;
- Contexto;
- Fontes;
- Atividade;
- Centro de Controle.

Actions, Workflows, Automations, Monitors, Connectors, Knowledge e módulos institucionais continuam no backend e são escolhidos pelo Jarvis.

## Conversação persistente

Cada conversa é gravada em `JarvisData/cognitive/conversations.db`.

Ao responder, o Jarvis pode recuperar:

- mensagens recentes;
- mensagens antigas lexicalmente relacionadas;
- lições relevantes aprendidas anteriormente.

Uma nova conversa não apaga o histórico.

## Aprendizado contínuo

O Learning Journal reconhece instruções explícitas como:

- `Prefiro fontes oficiais antes de blogs.`
- `Nunca publique sem me mostrar o rascunho.`
- `Da próxima vez, consulte a CCT primeiro.`
- `Lembre que ...`

As lições ficam persistentes e são recuperadas somente quando relevantes.

## Memória semântica opcional

A base funciona apenas com SQLite/FTS5. Para máquinas que suportem um modelo adicional de embeddings:

`install_semantic_memory_optional.bat`

Ele baixa e habilita `nomic-embed-text-v2-moe` pelo Ollama. A memória semântica é opcional e falhas nela não impedem o Jarvis de funcionar.

## Dados públicos

O novo Public Data Broker começa com 28 fontes catalogadas, entre fontes oficiais brasileiras, internacionais e plataformas abertas.

O fluxo é:

`pergunta → identificar domínio → recomendar fonte → consultar API/dataset → responder`

Quando não há adaptador:

`site → descobrir OpenAPI/RSS/Sitemap → proposta → integração aprovada`

Leia `PUBLIC_DATA_STRATEGY.md` e `PUBLIC_DATA_SOURCES.md`.

### Camada São Paulo

Como o projeto será usado no contexto do SindPetshop-SP, o catálogo também conhece fontes estaduais e municipais: Dados Abertos SP, ALESP, ObservaSampa e GeoSampa. Elas ficam disponíveis ao broker, não viram novas abas.

## Instalação

Extraia em uma pasta nova e execute:

1. `install.bat`
2. `run_cognitive_test.bat`
3. `run_self_test.bat`
4. `run_foundation_test.bat`
5. `run_routing_test.bat`
6. `run_health_test.bat`
7. `run_browser_test.bat`
8. `run_jarvis.bat`

Teste online opcional das fontes públicas:

`run_public_data_online_test.bat`

## Hardware

O núcleo continua otimizado para a máquina de testes atual: Ryzen 5 5600GT, ~16 GB RAM, Radeon integrada e qwen3:4b em CPU/contexto 4096.

O modelo de embeddings é opcional justamente para permitir que a mesma arquitetura rode em máquinas mais fracas.


## Runtime adaptativo 1.0b

Para evitar que conversa básica use o modelo de raciocínio mais pesado:

- `qwen3:1.7b`: conversa rápida;
- `qwen3:4b`: raciocínio e ferramentas.

Execute `install_fast_model.bat` uma vez após a instalação.
