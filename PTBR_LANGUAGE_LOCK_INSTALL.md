# Sind-AI — Language Lock pt-BR

Esta correção força a comunicação do Jarvis para português do Brasil sem alterar
a arquitetura de Observer, memória procedural, Swarm, Long-Horizon ou Skills.

## Por que foi necessário

O prompt principal já dizia para conversar em português, mas o Qwen FAST ainda
pode derivar para inglês em algumas respostas, especialmente em mensagens de erro
ou quando muito contexto em inglês entra na janela.

A correção trabalha em duas camadas:

1. reforça a regra pt-BR nos prompts principais;
2. adiciona uma barreira central antes de qualquer resposta pública ser persistida
   ou exibida.

A barreira só chama novamente o modelo quando detecta inglês dominante. Respostas
já em português não ganham latência adicional.

## Instalação

Extraia este overlay na raiz do repositório e execute:

```powershell
python .\apply_ptbr_language_lock.py
python .\run_ptbr_language_lock_tests.py
python -m compileall core cognitive
```

Depois valide:

```powershell
git diff
git status
```

Se estiver correto:

```powershell
git add .
git commit -m "fix: enforce Jarvis responses in pt-BR"
git push
```

## Teste manual recomendado

No Jarvis:

- `olá jarvis`
- `explique o que você é`
- abra uma página em inglês e peça `resuma isso`
- provoque uma tarefa que anteriormente retornava mensagem de erro

A comunicação do Jarvis deve permanecer em pt-BR.

Código, comandos, URLs, nomes de ferramentas e termos técnicos podem continuar
no formato original quando necessário.
