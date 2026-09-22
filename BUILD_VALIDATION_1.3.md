# Build Validation — Jarvis Personal GPT 1.3

## Validado offline

- Python compileall
- updater_test.py
- personal_gpt_test.py
- cognitive_test.py
- self_test.py
- foundation_regression_test.py
- JavaScript desktop syntax
- JavaScript portal syntax
- Service Worker syntax
- npm run build

## Updater

- commit igual em `main` → nenhuma atualização;
- commit diferente → atualização detectada;
- canal `stable` → versão semântica;
- `1.3 == 1.3.0`;
- helper externo presente;
- estado do updater isolado/persistente.

## Mobile

O runtime inclui diagnóstico de:
- bind do servidor;
- loopback TCP;
- IPv4 privados;
- perfil de rede Windows;
- regra de Firewall.

A conectividade celular real precisa ser validada no Windows/rede física do usuário.
