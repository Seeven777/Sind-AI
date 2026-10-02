# Probe de resultados de busca do WhatsApp

Este diagnóstico não depende do matcher atual de contatos.

Ele:
1. conecta ao WhatsApp;
2. localiza o campo de pesquisa;
3. escreve apenas `Me (você)` na pesquisa;
4. NÃO abre nenhuma conversa;
5. salva os controles UIA do painel esquerdo, incluindo ancestrais e padrões.

Execute:

```powershell
.\.venv\Scripts\python.exe .\probe_whatsapp_search_results.py --contact "Me (você)"
```

O arquivo criado será:

```text
probe_resultados_busca.json
```

Envie esse arquivo para análise.
