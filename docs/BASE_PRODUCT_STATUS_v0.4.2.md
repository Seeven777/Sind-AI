# Jarvis Next v0.4.2

## Correção principal

O provider nativo do Ollama agora trata explicitamente modelos com canal de pensamento.

- consulta `/api/show`;
- desativa thinking quando suportado e quando usando Qwen 3.x/3.5;
- nunca usa `message.thinking` como resposta final;
- se `/api/chat` retorna HTTP 200 com `message.content` vazio, faz uma segunda tentativa controlada com `think:false` e orçamento de saída maior;
- `model-probe` testa inferência real, não apenas presença do modelo;
- Setup e Validate verificam inferência antes de declarar Brain/Research como funcionais.

Isso corrige o caso real observado no Windows onde `qwen3.5:4b` estava instalado e saudável em `/api/tags`, mas o Research Agent recebia uma resposta com conteúdo final vazio.
