# UI / Productividade — Jarvis RC3

Esta versão trata o Companion como aplicativo de uso diário e o HQ como superfície de observabilidade.

### Decisões

**Companion** é a interface de conversa e histórico. A conversa é persistente e o histórico anterior é fornecido ao modelo como contexto; isso evita que cada mensagem seja tratada como sessão isolada.

**HQ** é uma experiência 3D interativa e não uma segunda fonte de verdade. Estados visuais continuam derivados de `/api/hq`.

**Histórico** usa a tabela existente `conversations/messages` e adiciona `pinned`/`archived` em migration 0006. Não é necessário recriar o banco.

**Compatibilidade**: `/hq-classic` preserva a superfície 2D anterior.
