# Build Validation — Jarvis Personal GPT 1.4

Validações específicas:

- configuração padrão sem deadline do LLM;
- configuração padrão sem deadline total da tarefa;
- `OllamaClient.chat(..., timeout=0)` não envia timeout de socket;
- Agent Runtime aplica deadline apenas quando valor > 0;
- heartbeat visual presente;
- tempo decorrido formatado e enviado à UI;
- JavaScript exibe detalhe real do runtime;
- testes cognitivos anteriores continuam ativos.

O botão Parar continua sendo a saída manual para tarefas que o usuário não deseja mais aguardar.
