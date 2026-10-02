# Security Model — Jarvis Next 1.0 RC2

## Princípio

Autonomia é limitada por capacidade + política + evidência.

## Riscos

- READ: automático
- PREPARE: automático
- INTERNAL_WRITE: aprovação
- EXTERNAL_WRITE: aprovação
- DESTRUCTIVE: aprovação
- FINANCIAL: bloqueado
- CREDENTIAL: bloqueado

## Secrets

`SecretStore` usa Windows DPAPI quando executado no Windows.

Tokens Google também usam DPAPI.

Secrets não devem ser colocados no repositório.

## Web Fetch

`web.fetch` bloqueia:

- loopback
- endereços privados
- link-local
- multicast
- reserved

Isso reduz SSRF contra serviços locais.

## Browser

Playwright é isolado como recurso opcional.

Ações de preenchimento/click passam pelo Policy Engine.

## Windows

Windows UI Automation usa pywinauto/UIA.

Não usamos coordenadas de mouse como caminho principal.

## WhatsApp

`whatsapp.send_message` é EXTERNAL_WRITE.

A execução precisa:

1. aprovação;
2. localizar contato;
3. localizar campo;
4. enviar;
5. observar o texto enviado;
6. somente então retornar sucesso.

## Skills

Código gerado:

- nasce em `skill_staging`;
- não altera `/src`;
- passa por static guard;
- precisa de testes;
- só é instalado depois;
- executa com `python -I` em subprocesso.

Esse isolamento não equivale a uma VM/Windows Sandbox. Skills não confiáveis devem permanecer desabilitadas.

## Local Only

`privacy.mode = "local_only"` remove integrações externas do runtime.

## Worker remoto

Ao expor worker fora de localhost, `JARVIS_WORKER_TOKEN` é obrigatório.

## Core

Nenhuma skill, agente customizado ou connector recebe autorização para reescrever o Core automaticamente.
