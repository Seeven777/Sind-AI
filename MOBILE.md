# Jarvis Mobile — diagnóstico e acesso

## Importante

Se a barra lateral não mostra **Jarvis Mobile**, essa instalação ainda está em uma versão anterior à 1.2.
Atualize manualmente uma única vez usando `Install-Jarvis.ps1` da versão 1.3. Depois disso, o Auto Updater passa a cuidar das próximas versões.

## Uso

1. Abra o Jarvis no computador.
2. Clique em **Jarvis Mobile**.
3. Clique em **Ativar acesso mobile**.
4. Mantenha computador e celular na mesma rede Wi-Fi/LAN.
5. Abra no celular um dos endereços exibidos, por exemplo `http://192.168.0.20:8770/`.
6. Informe o PIN de 6 dígitos.

## Se o celular não abrir o endereço

Use **Jarvis Mobile → Diagnosticar**.

A versão 1.3 verifica:

- se o servidor Mobile Companion está realmente ativo;
- se a porta responde localmente;
- perfil de rede do Windows;
- existência da regra `Jarvis Mobile Companion` no Firewall;
- todos os IPv4 privados detectados no computador;
- endereços alternativos para máquinas com Ethernet, Wi-Fi, VPN ou adaptadores virtuais.

Se o Firewall ainda não estiver liberado, use **Liberar no Firewall**.

A regra é criada apenas para redes **Private**. Se o diagnóstico mostrar que a rede atual do Windows está como **Public**, altere o perfil dessa rede para Privado antes de usar o companion.

## Segurança

- não encaminhe a porta TCP 8770 no roteador;
- o serviço foi projetado para LAN;
- o companion exige PIN e cria uma sessão temporária;
- troca do PIN invalida as sessões mobile;
- clientes externos à rede privada/loopback/link-local são recusados;
- modelos, memória e ferramentas continuam no computador, não no celular.

## Atualização

A partir da 1.3, o Jarvis verifica o GitHub automaticamente.

A instalação antiga precisa receber a 1.3 manualmente uma única vez. Depois:

`GitHub push → Jarvis detecta → Atualizações → Atualizar agora → backup → update → restart`

O canal padrão é `main` durante o desenvolvimento. O canal `stable` fica preparado para GitHub Releases.
