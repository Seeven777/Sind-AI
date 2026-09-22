# Jarvis Personal GPT 1.2 — Experience + Mobile

Esta release não expande o catálogo cognitivo. O foco é experiência de uso.

## Desktop UI

- novo visual mais imersivo e menos cru;
- sidebar mais limpa;
- composer redesenhado;
- welcome state com identidade visual própria;
- contexto/controle continuam secundários;
- painel dedicado ao Mobile Companion;
- estados visuais mais claros para execução, projeto e runtime.

## Mobile Companion

- servidor local opt-in na porta 8770;
- pareamento por PIN de 6 dígitos;
- sessão móvel temporária;
- chat com o mesmo Jarvis do PC;
- histórico de conversas;
- troca/criação de conversas;
- contexto do projeto atual;
- anexos de até 15 MB enviados do celular para a Knowledge Base;
- processamento continua no computador.

## Vercel/PWA

- launcher redesenhado;
- manifesto PWA com ícones 192/512;
- service worker/offline shell;
- fluxo de instalação Android;
- instrução específica para iPhone;
- página Mobile com conexão ao PC local.

## Segurança

- Mobile Companion desligado por padrão;
- regra de firewall opcional limitada a redes privadas;
- não existe relay cloud de prompts;
- não abra a porta 8770 para a internet.
