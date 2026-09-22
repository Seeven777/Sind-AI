# Build Validation — Jarvis Personal GPT 1.2

## Foco da release

- UI desktop refinada;
- Vercel/PWA refinada;
- Mobile Companion local;
- nenhuma expansão artificial do catálogo cognitivo.

## Validação offline

- Python compileall: OK
- JavaScript desktop: OK
- JavaScript Vercel/PWA: OK
- Service Worker JS: OK
- `mobile_companion_test.py`: OK
- `personal_gpt_test.py`: OK
- `cognitive_test.py`: OK
- `self_test.py`: OK
- `foundation_regression_test.py`: OK
- `npm run build`: OK
- `vercel_dist/` gerado: OK

## Mobile Companion

Validado no teste automatizado:

- start/stop do servidor;
- status público mínimo;
- pareamento por PIN;
- sessão por token;
- snapshot;
- chat;
- bloqueio de clientes fora de rede privada/loopback;
- rate limit de pareamento;
- processamento permanece no Jarvis do computador.

## Segurança mobile

- desligado por padrão;
- PIN de 6 dígitos;
- troca de PIN invalida sessões;
- sessão expira;
- limite de tentativas de pareamento;
- aceita somente IP privado/loopback/link-local;
- firewall opcional limitado ao perfil Private;
- documentação alerta para não encaminhar a porta 8770 à internet.

## PWA

- manifest com nome, start_url, display e ícones 192/512;
- service worker;
- modo standalone;
- fluxo `beforeinstallprompt` quando suportado;
- instrução manual específica para iPhone;
- portal não executa Python/Ollama.

## Testes que continuam dependentes do Windows real

- PySide/WebEngine renderizado;
- firewall do Windows;
- acesso LAN do celular;
- Ollama real;
- browser/desktop automation;
- sessões autenticadas dos serviços profissionais.
