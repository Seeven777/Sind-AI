# Fase 4 — correção do roteamento de intenção multilinha

Corrige o caso em que `não envie` em uma etapa intermediária fazia o pedido inteiro
ser classificado como informativo, mesmo quando havia comandos físicos antes/depois.

Agora a negação é local. Exemplo suportado:

```text
abra o WhatsApp
selecione a conversa Me (você)
escreva "teste fase 4" no campo de mensagem, mas não envie
envie a mensagem
```

O parser também extrai o contato e o texto dessa sequência para que o executor
WhatsApp determinístico possa operar sem o modelo inventar esses dados.

## Instalação

1. Feche o Jarvis completamente.
2. Extraia o ZIP overlay na raiz do projeto e substitua os arquivos.
3. Execute:

```powershell
python .\run_phase4_intent_regression.py
python .\run_phase4_tests.py
python -m compileall runtime core access acquisition
```

## Teste manual

Primeiro teste de forma atômica:

```text
Abra o WhatsApp
```

Depois:

```text
Selecione a conversa Me (você)
```

Depois:

```text
Escreva "teste fase 4" no campo de mensagem, mas não envie
```

E então:

```text
Envie a mensagem
```

Por último, teste o comando multilinha completo.

Não faça merge na `main` antes dos testes reais do desktop.
