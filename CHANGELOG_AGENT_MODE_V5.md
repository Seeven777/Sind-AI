# Jarvis Presence / Agent Mode v5

## Objetivo

Consolidar as correções pedidas após a v4: internet real como capacidade básica, modelos locais por função, voz mais resiliente, Office coerente e um cliente mobile do mesmo Jarvis.

## Alterações

### Internet autônoma
- `web.search` + `web.fetch` são tratados como capacidade básica de leitura quando o modo de privacidade permite rede.
- Pedidos de informação atual (notícias, clima, dados em tempo real e pesquisa web) são roteados automaticamente para Research.
- O Jarvis recebe no contexto do runtime o estado real da capacidade de internet e não precisa pedir ativação manual do Operator para pesquisa pública.
- Busca pública ganhou fallback estruturado Bing RSS além de DuckDuckGo/Bing HTML.
- O painel Sistema mostra o estado da Internet separadamente.

### Agentes e modelos
- Model Router agora possui perfil local por capacidade (`fast`, `coding`, `reasoning`, `creative`, `tool_use`).
- Todos os agentes disponíveis exibem um modelo atribuído, mesmo antes da primeira execução.
- Inbox e Memory Curator agora podem usar um modelo leve para interpretação, mantendo fallback determinístico se o LLM falhar.
- Operator registra o modelo de `tool_use` associado à função, sem fingir que um LLM executou a ferramenta.
- Instalador opcional automático:
  - `llama3.2:1b` para tarefas rápidas/triagem/memória.
  - `qwen2.5-coder:3b` para Developer.
- Se os modelos auxiliares não estiverem instalados, o modelo principal continua sendo usado automaticamente.

### Voz
- Fallback Windows passou a testar dois motores: `System.Speech` e `SAPI.SpVoice`.
- Cadeia da Companion: áudio gerado pelo backend -> Web Speech com confirmação real de início -> SAPI nativo no desktop.
- O fallback do navegador só é considerado ativo quando `onstart` realmente ocorre, evitando falso sucesso silencioso.
- No celular, SAPI do PC não é usado como fallback; a voz permanece no dispositivo via áudio/Web Speech.
- `Test-Jarvis-Voice.cmd` e botão `Testar voz agora` validam a cadeia de voz.

### Agent Office
- Corrigida a orientação dos monitores: a superfície emissiva agora fica voltada para os agentes.

### Mobile
- A mesma instância do Jarvis pode ser acessada pelo celular na mesma rede local.
- Servidor liga em LAN somente quando iniciado em `--mobile` (o launcher padrão v5 já usa esse modo).
- Acesso remoto local é protegido por token aleatório persistido no SecretStore/DPAPI do Windows.
- Localhost continua sem atrito.
- O token inicial é convertido em cookie HttpOnly/SameSite e removido da URL após autenticação.
- `Enable-Jarvis-Mobile.cmd` libera somente a porta 4760 no perfil de rede **Privada** do Windows.
- `Start-Jarvis-Mobile.cmd` mostra/copia o link protegido.
- Preferências da Companion possuem `Copiar acesso para celular`.

### Validação
- `Validate-Jarvis-Complete.ps1` agora inicia a UI com mobile protegido e verifica `/api/mobile` e `/api/voice/diagnostics`.
- Novo conjunto de testes v5 cobre roteamento web, modelos por função, orientação dos monitores, cadeia de voz e token mobile.
