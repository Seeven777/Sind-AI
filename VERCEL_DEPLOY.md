# Deploy na Vercel — Jarvis Personal GPT 1.2

A Vercel hospeda somente o launcher/PWA. O Jarvis real continua executando localmente.

## Arquitetura

```text
Vercel HTTPS
  └─ PWA / launcher / instalador
          |
          +─ Windows: jarvis://open
          |
          +─ Mobile: abre o Mobile Companion do PC na rede local

Computador
  ├─ Jarvis Cognitive Core
  ├─ Ollama
  ├─ memória / arquivos
  ├─ automação
  └─ Mobile Companion :8770
```

## Configuração Vercel

O repositório já contém:

- `vercel.json`
- `package.json`
- `vercel_build.cjs`
- `vercel_portal/`

Build:

`npm run build`

Output:

`vercel_dist`

## PWA mobile

O portal inclui:

- manifest;
- ícones 192/512;
- service worker;
- botão de instalação em navegadores compatíveis;
- instrução iPhone;
- tela para abrir o endereço do Mobile Companion.

A PWA não processa prompts. Ela funciona como launcher e interface de distribuição.
