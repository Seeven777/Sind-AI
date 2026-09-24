# Probe automático da conversa do WhatsApp

Este diagnóstico elimina a perda de foco causada por trocar do WhatsApp para o
PowerShell.

Ele:

1. conecta ao WhatsApp;
2. encontra o campo de pesquisa;
3. pesquisa o contato solicitado;
4. abre o resultado exato;
5. imediatamente inspeciona a árvore UI Automation da conversa;
6. salva tudo diretamente em JSON UTF-8.

Ele **não digita mensagem e não envia nada**.

Execute na raiz do JARVIS:

```powershell
.\.venv\Scripts\python.exe .\probe_whatsapp_conversation.py --contact "Me (você)"
```

O arquivo será criado automaticamente:

```text
probe_conversa_aberta.json
```

Envie esse JSON para análise.

Não use redirecionamento `>`; o próprio script grava UTF-8.
