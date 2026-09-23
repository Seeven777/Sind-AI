# Jarvis Personal GPT 1.4.1 — UX Stability

## Corrigido

- rolagem da conversa no desktop;
- grid central usa `minmax(0,1fr)` para o painel de chat poder realmente encolher e rolar;
- scrollbar visível no histórico;
- wheel fallback para Qt WebEngine;
- Page Up / Page Down no histórico;
- Ctrl+Home / Ctrl+End;
- botão flutuante **Última mensagem**;
- nova mensagem não arranca o usuário da posição de leitura quando ele está lendo conteúdo antigo;
- respostas internas `<think>` são removidas globalmente antes de chegar à UI;
- mensagens antigas com `</think>` também são limpas na renderização;
- Jarvis Mobile passa a ser descrito corretamente como interface do PC host;
- `Abrir WhatsApp` ganha Fast Path e não precisa chamar o qwen3:4b.

## Comportamento esperado

Respostas longas podem ter qualquer tamanho. A área central continua rolável independentemente do tamanho da mensagem.

O Jarvis não deve mais exibir raciocínio interno em inglês, chain-of-thought ou tags `<think>`.
