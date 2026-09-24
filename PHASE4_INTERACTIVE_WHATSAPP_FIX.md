# Fase 4 — correção de interação multi-turn no WhatsApp Desktop

## Diagnóstico da captura de 24/09/2026

A captura confirma que a falha ocorre **antes** da navegação UIA da conversa.

O comando:

```text
abra o WhatsApp
selecione a conversa Me (você)
```

estava sendo interceptado pelo `core/router.py`. O Fast Path antigo aceitava qualquer texto que contivesse simultaneamente `abra` e `WhatsApp` e retornava imediatamente `open_app`. Assim, `selecione a conversa...` era descartado.

Também havia dois limites adicionais:

1. `escreva` não fazia parte dos verbos físicos do classificador da Fase 4, então frases como `escreva no chat aberto do WhatsApp: "teste 1"` podiam cair no modo de conversa em vez de executar.
2. O executor determinístico original do WhatsApp exigia contato + texto + envio no mesmo turno. Ele não mantinha um estado verificável entre `selecionar conversa` -> `digitar rascunho` -> `enviar`.

## O que esta correção muda

- O Fast Path só abre o WhatsApp quando o pedido é **somente** `abra o WhatsApp` (ou equivalente). Comandos compostos não são mais truncados.
- `escreva`, `escrever`, `insira` e `preencha` podem ser reconhecidos como ações físicas quando usados em contexto de interface.
- É adicionado um runtime determinístico de WhatsApp multi-turn.
- O estado mantido entre turnos contém apenas o contato verificado, o rascunho verificado e um marcador de incerteza. O estado **não substitui observação da tela**: cada etapa revalida conversa e campo antes de agir.
- `não envie` continua sendo uma proibição local. Digitar um rascunho não autoriza o envio.
- `envie a mensagem` só funciona como continuação quando o Jarvis possui uma conversa previamente verificada; antes de enviar ele relê o cabeçalho e o rascunho.
- Se já existir outro rascunho, ele é preservado. O Jarvis não sobrescreve silenciosamente.
- Se o botão Enviar tiver sido acionado e a confirmação posterior falhar, o resultado continua sendo `Envio incerto`; não há reenvio automático.
- A confirmação configurada em `deep_access.confirm_risky_controls` continua valendo para o envio.

## Instalação

Este pacote é complementar à Fase 4 e ao Intent Fix anterior. Não aplique sobre a `main` sem testar.

1. Feche totalmente o Jarvis, inclusive o ícone da bandeja.
2. Extraia este ZIP **na raiz atual do projeto**, substituindo os arquivos existentes.
3. Abra PowerShell nessa raiz.
4. Rode o patch cirúrgico de `core/agent.py`:

```powershell
.\.venv\Scripts\python.exe .\apply_phase4_whatsapp_interactive_fix.py
```

Se não estiver usando `.venv`:

```powershell
python .\apply_phase4_whatsapp_interactive_fix.py
```

O script cria, uma única vez, o backup:

```text
core/agent.py.phase4-interactive.bak
```

Depois execute:

```powershell
.\.venv\Scripts\python.exe .\run_phase4_interactive_tests.py
.\.venv\Scripts\python.exe .\run_phase4_tests.py
.\.venv\Scripts\python.exe -m compileall core runtime access
```

O primeiro conjunto possui 13 testes de regressão e executor simulado.

## Teste manual recomendado

Reinicie completamente o Jarvis e use **uma conversa nova de teste**.

### 1. Abrir e selecionar

```text
abra o WhatsApp
selecione a conversa Me (você)
```

Resultado esperado: o WhatsApp abre, a pesquisa é usada, a conversa é aberta e o Jarvis responde que confirmou a conversa. Ele não deve parar apenas em `Aplicativo aberto: WhatsApp`.

### 2. Digitar sem enviar

```text
escreva "teste fase 4" no campo de mensagem, mas não envie
```

Resultado esperado: o texto aparece no compositor e permanece como rascunho. A resposta deve afirmar que o texto foi relido e que nada foi enviado.

### 3. Enviar o rascunho

```text
envie a mensagem
```

Resultado esperado: após a confirmação configurada, o Jarvis aciona Enviar uma única vez e procura uma nova mensagem de saída com o texto exato.

### Outra forma aceita

```text
escreva no chat aberto do whatsapp: "teste 1"
```

Ela reutiliza a conversa anteriormente verificada. Se houver outro rascunho, a operação é bloqueada para não sobrescrevê-lo.

## Teste atômico da Fase 4 original

Este caminho continua existindo e é útil para isolar problemas de UI Automation:

```text
Envie no WhatsApp para Me (você): teste fase 4
```

Esse formato entra diretamente no executor de envio completo já existente. Se o comando multi-turn falhar após esta correção, a mensagem de erro deverá indicar a etapa UIA concreta (campo de pesquisa, contato, cabeçalho, compositor ou botão Enviar), em vez de simplesmente abrir o aplicativo e encerrar.

## Arquivos do overlay

- `runtime/phase4/whatsapp_interactive.py` — parser e executor determinístico multi-turn.
- `runtime/phase4/intent.py` — verbos de escrita desktop e Intent Fix preservado.
- `core/router.py` — Fast Path de abertura restrito a pedidos atômicos.
- `access/commands.py` — aliases de digitação natural.
- `apply_phase4_whatsapp_interactive_fix.py` — integração cirúrgica em `core/agent.py` sem substituir o arquivo inteiro.
- `run_phase4_interactive_tests.py`
- `tests/test_phase4_whatsapp_interactive.py`

Não há API paga, OCR, coordenadas fixas nem fallback para WhatsApp Web nesta correção.
