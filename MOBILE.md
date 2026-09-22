# Jarvis Mobile Companion — 1.2

## O que é

O Mobile Companion transforma o telefone em uma interface para o mesmo Jarvis que está rodando no computador.

O celular **não executa Ollama, automação de Windows nem a memória principal**. O computador continua sendo o runtime.

## Uso na mesma rede

1. Abra o Jarvis no Windows.
2. Clique em **Jarvis Mobile** na lateral ou use o ícone da bandeja.
3. Ative o acesso mobile.
4. O Jarvis exibirá um endereço como `http://192.168.0.20:8770/` e um PIN de 6 dígitos.
5. Conecte o celular à mesma rede Wi‑Fi.
6. Abra o endereço no navegador e digite o PIN.

O pareamento cria uma sessão temporária. Trocar o PIN invalida as sessões anteriores.

## Firewall

Se o telefone não conseguir abrir o endereço, execute:

`enable_mobile_access.bat`

A regra criada aceita TCP 8770 apenas no perfil **Private** do Firewall do Windows.

Para remover:

`disable_mobile_access.bat`

## Instalação no celular

O portal da Vercel é uma PWA instalável via HTTPS e funciona como launcher/distribuidor.

No Android, navegadores compatíveis podem mostrar **Instalar app**.

No iPhone, use **Compartilhar → Adicionar à Tela de Início** e **Abrir como App** quando a opção estiver disponível.

A interface completa do Mobile Companion é servida pelo computador local. Em uma rede LAN HTTP ela pode ser usada normalmente no navegador; a PWA hospedada na Vercel continua sendo o app instalável e o ponto de entrada.

## Segurança

- Mobile Companion fica desligado por padrão.
- Acesso é feito por PIN e token temporário.
- Nenhum PIN é enviado à Vercel.
- O servidor deve permanecer restrito à rede privada.
- Não encaminhe a porta 8770 no roteador para a internet.
