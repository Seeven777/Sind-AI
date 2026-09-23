# Mobile Route Fix 1.3.2

Corrige o erro observado:

`GET http://<IP>:8770/068112 404 (Not Found)`

`068112` é um PIN de seis dígitos sendo anexado ao caminho da URL por um handler do navegador/ambiente (`default_video_handler.js`).

A partir da 1.3.2:

- `/123456` é uma rota válida do Jarvis Mobile;
- a interface mobile abre normalmente;
- o JavaScript extrai o PIN do pathname;
- remove o PIN da barra de endereço;
- autentica usando o endpoint correto `POST /api/pair`;
- rotas SPA sem extensão deixam de gerar 404;
- assets inexistentes continuam retornando 404 normalmente;
- subprocessos de detecção de hardware no Windows também passam a rodar sem janela visível.

O arquivo `default_video_handler.js` não pertence ao Jarvis. A correção torna o servidor compatível com o comportamento que ele está produzindo.
