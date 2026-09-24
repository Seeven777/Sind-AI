# Raw Search Result Probe

Este probe corrige uma falha do diagnóstico anterior: ele não usa
`choose_text_field()` para localizar a busca.

Ele trabalha diretamente sobre os nós UIA `Edit` expostos pelo WebView2.

## Segurança

O script:
- escreve somente o nome do contato no campo de pesquisa;
- não abre conversa;
- não escreve mensagem;
- não envia nada.

## Executar

```powershell
.\.venv\Scripts\python.exe .\probe_whatsapp_search_results_raw.py --contact "Me (você)"
```

O arquivo criado é:

```text
probe_resultados_busca_raw.json
```

O próprio Python grava UTF-8. Não use `>`.

Envie o JSON resultante para análise.
