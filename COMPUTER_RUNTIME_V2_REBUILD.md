# Sind AI / Jarvis — Computer Runtime V2 Rebuild

## Por que este rebuild existe

A sequência de microcorreções isolou vários problemas reais (MSIX/WebView2,
UIA, seleção de contato, composer), mas a captura final mostrou um problema de
arquitetura: o pedido composto ainda podia terminar no caminho genérico de
`open_app`, respondendo apenas `Aplicativo aberto: WhatsApp`.

Computer Runtime V2 trata roteamento e execução física como duas camadas
separadas e testáveis.

## O que foi reconstruído

### 1. Precedência de execução

`apply_computer_runtime_v2.py` instala um guard determinístico no início de
`JarvisAgent._run_internal`:

- comandos compostos do WhatsApp são analisados antes do fast path genérico;
- `abra WhatsApp + selecione conversa` não pode ser reduzido a `open_app`;
- um envio atômico completo continua no executor de envio existente;
- continuação `envie a mensagem` só usa estado previamente verificado.

### 2. Runtime de computador genérico

`runtime/computer_v2.py` adiciona primitivas locais e gratuitas:

- foco robusto de HWND;
- input físico de mouse;
- contexto DPI Per-Monitor V2;
- atalhos de teclado (`ctrl+f`, `ctrl+a`, `alt+f4`, PageDown etc.);
- digitação Unicode por clipboard com restauração do clipboard do usuário;
- leitura de texto focado sem envio;
- coordenadas sempre derivadas de bounds reais da interface, nunca fixas.

`access/controller.py` continua expondo a mesma API já usada pelo Jarvis, mas
passa a usar UI Automation + fallback físico verificado. Isso amplia a
capacidade para outros aplicativos Windows, não apenas WhatsApp.

### 3. WhatsApp Desktop V2

O WhatsApp continua usando a descoberta MSIX/WebView2 que já funcionou, mas a
abertura da conversa muda de estratégia:

1. pesquisa e valida o contato exato;
2. tenta navegação de teclado a partir da pesquisa: `Down -> Enter`;
3. verifica o cabeçalho da conversa;
4. se necessário, usa clique físico DPI-aware nos bounds UIA atuais;
5. tenta double-click somente como fallback;
6. só considera sucesso se o contato solicitado aparecer no painel direito.

Para o composer, se WebView2 não expuser um `Edit` real, o runtime cria um alvo
lógico baseado na geometria da conversa, foca fisicamente o campo, digita via
clipboard Unicode e copia o conteúdo de volta para verificar o texto literal.

Enviar continua sendo operação separada: Enter só pode ocorrer no caminho de
envio explicitamente autorizado e após reler conversa + rascunho. O runtime
nunca repete um envio incerto automaticamente.

## Instalação limpa

Feche completamente o Jarvis antes de aplicar.

Extraia o ZIP sobre a raiz:

```text
C:\Users\AMD\Desktop\JARVIS
```

Execute:

```powershell
.\.venv\Scripts\python.exe .\apply_computer_runtime_v2.py
```

O instalador:

- cria backup de `core/agent.py`;
- instala precedência do Runtime V2;
- arquiva testes de micro-patches antigos que verificavam estratégias já
  substituídas;
- é idempotente.

## Validação

### A. Testes do rebuild

```powershell
.\.venv\Scripts\python.exe .\run_computer_v2_tests.py
```

A suíte incluída possui 21 testes locais do runtime/roteamento e deve terminar
com `OK`.

### B. Wiring carregado

```powershell
.\.venv\Scripts\python.exe .\computer_v2_diagnose.py
```

Esperado:

```json
{
  "ok": true,
  "router_fast_path_for_compound": null,
  "interactive_parse": {
    "select": true,
    "contact": "Me (você)"
  },
  "early_route_marker_loaded": true
}
```

### C. Benchmark físico sem Jarvis

```powershell
.\.venv\Scripts\python.exe .\computer_v2_benchmark.py --contact "Me (você)"
```

Esse teste ignora o roteador/conversa do Jarvis e testa diretamente o runtime
Windows. Ele **não digita mensagem e não envia nada**.

Esperado:

```text
"ok": true
...
"conversation_verified"
```

Opcionalmente, depois que a conversa abrir:

```powershell
.\.venv\Scripts\python.exe .\computer_v2_benchmark.py --contact "Me (você)" --draft "teste runtime v2"
```

Isso pode digitar e verificar apenas o rascunho. Não envia.

### D. Jarvis completo

Encerre qualquer processo antigo do Jarvis e abra a aplicação novamente. Teste:

```text
abra o WhatsApp
selecione a conversa Me (você)
```

A resposta `Aplicativo aberto: WhatsApp` sozinha não é mais aceitável para esse
pedido composto. O runtime precisa abrir/verificar a conversa ou informar a
falha de verificação.

Depois:

```text
escreva "teste runtime v2" no campo de mensagem, mas não envie
```

Só após esses dois benchmarks deve-se testar envio.

## Escopo do objetivo “controlar o computador”

A arquitetura deixa de depender de receitas específicas para cada aplicativo.
A base genérica é: selecionar janela -> observar UIA -> agir semanticamente ->
fallback físico -> observar novamente -> verificar a pós-condição.

Isso permite expandir o mesmo mecanismo para editores, navegadores, sistemas
internos, Explorer, menus, formulários e outros aplicativos. Barreiras do próprio
Windows (UAC/secure desktop), credenciais que o usuário não forneceu e ações que
exigem confirmação continuam sendo limites de segurança/OS, não limitações de
planejamento da IA.
