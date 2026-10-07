# Jarvis Mobile v6

A tela `/mobile` é um cliente dedicado do **mesmo Jarvis** executado no computador. Não cria outro assistente: usa a mesma conversa, memória, missões, agentes, atenção e voz.

## Uso rápido — mesma rede Wi-Fi

1. Execute `Upgrade-Jarvis-v6.cmd` ou `Start-Jarvis-Mobile.cmd`.
2. Abra no celular o link exibido/copiado pelo script.
3. Texto, histórico, respostas faladas e estado do Jarvis funcionam diretamente contra o runtime do PC.

O acesso LAN possui token e a regra de firewall criada pelo projeto é limitada ao perfil de rede privada.

## Uso recomendado — HTTPS privado

Execute `Enable-Jarvis-Mobile-Secure.cmd`.

O script instala/configura Tailscale quando necessário e publica somente o Jarvis dentro da sua tailnet usando HTTPS. Instale Tailscale também no celular e use a mesma conta/tailnet.

Essa rota permite que recursos que navegadores bloqueiam em HTTP — especialmente microfone e instalação PWA — funcionem em contexto seguro.

Para retirar a publicação privada: `Disable-Jarvis-Mobile-Secure.cmd`.

## Interface

A versão móvel possui:

- Jarvis Core vivo;
- chat e histórico do mesmo runtime;
- campo de comando fixo;
- entrada por voz quando o navegador permite;
- respostas faladas pelo backend de voz do PC;
- atenção/notificações;
- menu para Office, Missões, Agentes, Projetos, Memória e Sistema;
- instalação como PWA em HTTPS.

## Limite atual

O processamento principal continua no computador. O celular é uma superfície remota do Jarvis. Isso é intencional nesta etapa: mantém memória e ferramentas centralizadas e evita criar dois Jarvis divergentes.
