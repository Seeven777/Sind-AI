# Sind AI — Computer Runtime V3 Raw Bridge

## Por que o V2 falhou no benchmark real

O seu diagnóstico raw já havia mostrado que o WhatsApp atual expõe:

```text
Edit
name=""
automation_id="_r_f_"
bounds=[1283,208,1407,229]
```

Ou seja, o campo global de pesquisa pode ficar **sem nome acessível**.

O V2 ainda dependia de `choose_text_field()` e de nomes normalizados em alguns
pontos. Isso explica dois sintomas reais:

```text
search_written
Resultado exato/único não apareceu: 0
```

e, na execução seguinte:

```text
Nenhum campo de texto editável, visível e seguro foi identificado.
```

## V3

A camada WhatsApp agora usa a árvore UIA bruta como fonte primária:

1. encontra o `Edit` raw por editabilidade + posição + label/id quando existirem;
2. escreve via ValuePattern e relê;
3. procura DataItems do contato diretamente em `Resultados da pesquisa`;
4. agrupa os DataItems duplicados do WebView2 em um único resultado lógico;
5. clica fisicamente usando os bounds atuais do resultado;
6. readquire a árvore após cada mudança de DOM;
7. verifica o cabeçalho pelo raw UIA do painel direito;
8. se o compositor não existir como Edit, usa região relativa ao painel direito,
   cola Unicode preservando o clipboard e relê o conteúdo;
9. benchmark nunca envia mensagem.

Não há coordenadas absolutas de tela.

## Instalação

Feche o Jarvis e extraia todo o overlay na raiz:

```text
C:\Users\AMD\Desktop\JARVIS
```

Depois:

```powershell
.\.venv\Scripts\python.exe .\apply_computer_runtime_v3.py
.\.venv\Scripts\python.exe .\run_computer_v3_tests.py
```

Benchmark sem digitação:

```powershell
.\.venv\Scripts\python.exe .\computer_v3_benchmark.py --contact "Me (você)"
```

Somente depois de `ok: true`, benchmark de rascunho:

```powershell
.\.venv\Scripts\python.exe .\computer_v3_benchmark.py --contact "Me (você)" --draft "teste runtime v3"
```

Nenhum dos dois envia mensagem.
