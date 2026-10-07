# Jarvis Mobile v5

O mobile é **o mesmo Jarvis**, não uma segunda instância: conversa, memória, missões, agentes e estado vêm do runtime do computador.

## Primeira ativação

1. Execute `Upgrade-Jarvis-v5.cmd` após aplicar o overlay. Ele prepara modelos auxiliares, solicita a regra de firewall privado e inicia o Jarvis.
2. Aprove o UAC do Windows quando solicitado para liberar somente a porta TCP 4760 em redes privadas.
3. No celular, conecte-se à mesma rede Wi-Fi do computador.
4. Execute `Start-Jarvis-Mobile.cmd` no computador ou abra Preferências -> `Copiar acesso para celular`.
5. Abra no celular o link protegido exibido.

O link contém um token somente no primeiro acesso. Depois da validação, o servidor grava uma sessão HttpOnly/SameSite e redireciona para a URL limpa.

## Limites desta versão

- É um cliente web móvel local, não um aplicativo nativo publicado em loja.
- Funciona enquanto o computador/Jarvis estiverem ligados e o celular estiver na mesma rede local.
- A instalação PWA e alguns recursos de microfone podem depender das regras de contexto seguro do navegador móvel quando usados por HTTP local. Texto, memória, missões e voz de saída continuam disponíveis pelos fallbacks implementados.
- Acesso fora de casa/rede local não é exposto automaticamente. Isso deve ser adicionado posteriormente com túnel/VPN autenticado, não abrindo uma porta pública diretamente.
