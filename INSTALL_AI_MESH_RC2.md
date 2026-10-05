# Jarvis RC2 — AI Mesh

Este pacote adiciona uma camada de integração opcional para:

- Hermes Agent instalado localmente;
- NVIDIA Nemotron 3 Ultra via endpoint OpenAI-compatible;
- WA-AKG como gateway WhatsApp opcional;
- Open Generative AI/Muapi como backend criativo opcional.

## 1. Aplicação

Pare o Jarvis antes de substituir os arquivos:

```powershell
cd C:\Users\AMD\Desktop\Sind-AI
.\Stop-Jarvis.cmd
```

Extraia o pacote mantendo a estrutura de pastas e substitua os arquivos.

Depois:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\Validate-Jarvis-Complete.cmd
```

O pacote contém a correção de afinidade de thread SQLite usada pela HQ e os testes novos da AI Mesh.

## 2. Diagnóstico

```powershell
.\AI-Status.cmd
```

O resultado esperado antes de configurar chaves é semelhante a:

- Hermes: `healthy` se o comando estiver no PATH;
- Nemotron: `unconfigured` sem `NVIDIA_API_KEY`;
- WA-AKG: `unconfigured` sem URL/sessão/chave;
- Creative Studio: `unconfigured` sem chave.

## 3. Hermes

O Jarvis chama o Hermes em modo one-shot e, por padrão, usa o toolset `safe`.
Isso evita que uma chamada consultiva conceda terminal, escrita de arquivos ou automação de navegador ao Hermes.

No chat do Jarvis:

```text
/hermes analise este problema e proponha um plano
```

No terminal:

```powershell
.\Hermes-Run.cmd "Analise este problema e proponha um plano"
```

## 4. Nemotron 3 Ultra

Não instale o checkpoint BF16 do Nemotron nessa máquina. O Jarvis usa o endpoint remoto da NVIDIA.

Configure a chave com o SecretStore:

```powershell
.\.venv\Scripts\python.exe -m jarvis secret-set nvidia_api_key
```

ou, somente para a sessão atual:

```powershell
$env:NVIDIA_API_KEY="SUA_CHAVE"
```

Teste:

```powershell
.\Nemotron-Probe.cmd
```

No chat do Jarvis, o modo explícito é:

```text
/deep faça uma análise profunda desta arquitetura
```

Sem Nemotron disponível, `/deep` cai para o modelo local; ele não inventa um modelo remoto saudável.

## 5. WA-AKG

O gateway não substitui o WhatsApp Desktop automaticamente.
Configure apenas depois de o WA-AKG estar funcionando isoladamente:

```powershell
.\.venv\Scripts\python.exe -m jarvis secret-set wa_akg_api_key
$env:JARVIS_WA_AKG_URL="http://127.0.0.1:3000"
$env:JARVIS_WA_AKG_SESSION="session_01"
```

Para configuração persistente, coloque URL e sessão na seção `[ai]` do arquivo:

`%LOCALAPPDATA%\JarvisNext\config\config.toml`

O envio pelo Desktop continua sendo o caminho oficial do Operator até existir verificação de entrega equivalente pelo gateway.

## 6. Creative Studio

Configure a chave:

```powershell
.\.venv\Scripts\python.exe -m jarvis secret-set creative_api_key
```

Teste a conexão:

```powershell
.\Creative-Doctor.cmd
```

Geração genérica por endpoint:

```powershell
.\.venv\Scripts\python.exe -m jarvis creative-generate "ENDPOINT_DO_MODELO" --params '{"prompt":"teste"}'
```

O endpoint é deliberadamente configurável, porque o catálogo de modelos do estúdio é atualizado separadamente do core do Jarvis.

## Regras mantidas

- Nenhuma integração externa recebe as permissões do `operations.operator`.
- Escritas externas continuam sujeitas a aprovação.
- Ações físicas continuam em `Observe -> Act -> Observe -> Verify`.
- Jarvis não considera um job criativo concluído sem um resultado retornado pela API.
- Um retorno HTTP de WA-AKG não é tratado sozinho como prova de entrega no WhatsApp.
