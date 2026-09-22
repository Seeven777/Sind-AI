# Build Validation — Cognitive Runtime 1.0b

- Python compileall: OK
- Conversational answer fallback: OK
- Institucional → public web fallback: OK
- Model routing module: OK
- UI footer FAST ↔ REASON: OK

## Testes no Windows

Execute:

1. `install.bat`
2. `install_fast_model.bat`
3. `run_model_router_test.bat`
4. `run_cognitive_test.bat`
5. `run_jarvis.bat`

Teste principal:

`quem é o sindpetshop-sp?`

O painel não deve criar uma tarefa de agente apenas para essa pergunta.

## Observação

O ambiente de build não executa o Ollama do PC do usuário. A velocidade real do
`qwen3:1.7b` deve ser validada no Ryzen 5 5600GT.
