# Cognitive Core — arquitetura alvo

```text
                         CONVERSA
                            │
                    Conversation Core
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
      MEMÓRIA          KNOWLEDGE          RESEARCH
    conversas/FTS      docs/CCTs          web/dados
    lições/regras      institucional       públicos
          │                 │                 │
          └─────────────────┼─────────────────┘
                            │
                     AGENT DECISION
                            │
              ┌─────────────┼─────────────┐
              │             │             │
           RESPONDER      PESQUISAR       AGIR
                            │             │
                      public broker   tool brokers
                                      │
                       ┌──────────────┼──────────────┐
                       │              │              │
                    desktop         browser       connectors
```

## Regra principal

O modelo não recebe um catálogo enorme. Ferramentas são selecionadas por contexto e a longa cauda fica atrás de brokers (`search_actions`, `find_public_sources`, `search_capabilities`, etc.).

## Memória

1. Conversa persistente: SQLite + FTS5.
2. Lições explícitas: preferências/correções/regras.
3. Memória semântica opcional: embeddings locais via Ollama; desligada por padrão para preservar hardware fraco.
4. Knowledge Base: documentos, CCTs e materiais institucionais.

## Aprendizado

Nesta fundação, “aprender” não significa retreinar os pesos do Qwen.

Significa acumular estado verificável:

- conversa;
- preferências;
- correções;
- episódios;
- documentos;
- Skills;
- padrões de uso;
- novas fontes/capabilities aprovadas.

Retreino/fine-tuning pode ser estudado no futuro, mas não é necessário para o comportamento de GPT pessoal.
