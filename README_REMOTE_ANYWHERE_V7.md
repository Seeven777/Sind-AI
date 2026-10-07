# Jarvis Anywhere — v7

O modo **Jarvis Anywhere** permite abrir o mesmo Jarvis em qualquer navegador, fora da rede local e sem instalar aplicativo no dispositivo cliente.

## Como funciona

- O Jarvis continua rodando no PC principal.
- O PC abre um túnel HTTPS de saída usando **Tailscale Funnel**.
- O celular, tablet ou outro computador acessa o endereço HTTPS público pelo navegador.
- O dispositivo cliente não precisa instalar Tailscale.
- O Jarvis continua usando a mesma memória, banco, agentes, missões, conectores e modelos do PC.
- O PC precisa permanecer ligado e conectado à internet.

## Ativar

Execute:

`Enable-Jarvis-Anywhere.cmd`

Na primeira ativação, o Tailscale pode abrir uma página para permitir o uso do Funnel. Depois disso a configuração roda em background e volta após reinicializações do Tailscale/Windows.

O script mostra dois links:

- **Mobile / tablet**: abre `/mobile`.
- **Outro computador**: abre o Companion completo.

O link mobile também é copiado para a área de transferência.

## Segurança

A URL pública do Funnel não é suficiente para controlar o Jarvis. A primeira conexão também exige o token remoto aleatório do Jarvis. Depois da validação, o token é removido da URL e guardado como cookie HttpOnly; quando o acesso passa por HTTPS o cookie recebe também a flag Secure.

O servidor diferencia acesso local real de tráfego que chegou por proxy/túnel, evitando que um proxy local seja confundido com localhost confiável.

## Ver endereço atual

`Jarvis-Anywhere-Status.cmd`

## Desativar

`Disable-Jarvis-Anywhere.cmd`

## Modo privado antigo

`Enable-Jarvis-Mobile-Secure.cmd` continua disponível para quem quiser acesso restrito aos próprios dispositivos da tailnet. Esse modo usa Tailscale Serve e exige Tailscale no dispositivo cliente.
