# Phase 4 — WhatsApp MSIX / WebView2 Fix

## Motivo

Na máquina de teste, o WhatsApp Microsoft Store 2.2636 usa `WhatsApp.Root.exe`.
A interface visual pode ser hospedada por processos filhos `msedgewebview2.exe`,
portanto procurar somente uma janela pertencente a `WhatsApp.exe` falha.

## O que muda

- descobre `WhatsApp.Root.exe`;
- monta a árvore de processos descendentes sem adicionar dependências;
- aceita a janela WebView2 pertencente à árvore do WhatsApp;
- ignora helpers WebView2 totalmente transparentes;
- conecta o HWND escolhido ao backend UIA;
- mantém compatibilidade com `WhatsApp.exe` antigo;
- `verify_open_app("whatsapp")` usa a mesma descoberta;
- `--probe` agora mostra root PIDs, candidatos, janela escolhida e campos UIA.

## Instalação

Feche o Jarvis e extraia o ZIP sobre a raiz do projeto, substituindo arquivos.

Depois:

```powershell
.\.venv\Scripts\python.exe .\run_phase4_tests.py
```

Com o WhatsApp Desktop aberto e visível:

```powershell
.\.venv\Scripts\python.exe .\run_phase4_tests.py --probe
```

O probe é somente leitura. Ele não abre conversa, não digita e não envia.

## Resultado esperado do probe

O JSON deve mostrar algo semelhante a:

```json
{
  "ok": true,
  "roots": [16492],
  "process_tree_size": 5,
  "candidates": [
    {
      "exe": "msedgewebview2.exe",
      "class_name": "Chrome_WidgetWin_1"
    }
  ],
  "chosen": {
    "exe": "msedgewebview2.exe"
  }
}
```

Também deve listar pelo menos o campo de pesquisa em `fields`.

Se `ok` passar para `true` mas `fields` vier vazio, o problema seguinte será a
árvore de acessibilidade do WebView2, não mais a descoberta da janela.

## Teste do Jarvis

Depois de o probe passar:

```text
abra o WhatsApp
selecione a conversa Me (você)
```

Depois:

```text
escreva "teste fase 4" no campo de mensagem, mas não envie
```

Não faça merge na main enquanto o fluxo não for validado fisicamente.
