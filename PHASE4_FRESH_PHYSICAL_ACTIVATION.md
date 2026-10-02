# Phase 4 — Fresh Physical Activation

## O que a captura provou

O painel direito continua neutro. O contato é localizado, mas a conversa não abre.

## Mudança

O caminho de abertura não usa mais Enter.

Agora:
1. usa o retângulo UIA vivo do resultado;
2. calcula um ponto dentro da área de texto do contato;
3. executa clique físico real nesse ponto;
4. verifica o cabeçalho no painel direito;
5. se falhar, refaz a pesquisa e obtém um wrapper novo;
6. tenta um segundo ponto com geometria nova;
7. readquire novamente antes de um double-click;
8. qualquer sucesso só é aceito se o cabeçalho aparecer.

Nenhuma coordenada de tela é fixa: os pontos vêm dos bounds UIA atuais.

## Teste

Extraia por cima do projeto.

```powershell
.\.venv\Scripts\python.exe .\run_phase4_tests.py
```

Reinicie o Jarvis e execute somente:

```text
abra o WhatsApp
selecione a conversa Me (você)
```

Ainda não digite nem envie mensagens.
