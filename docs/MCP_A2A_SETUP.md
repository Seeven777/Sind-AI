# MCP / A2A / Nodes

## MCP

Arquivo:

`%LOCALAPPDATA%\JarvisNext\config\mcp_servers.json`

Exemplo:

```json
[
  {
    "id": "example",
    "command": ["python", "server.py"],
    "enabled": true,
    "tools": ["lookup"]
  }
]
```

Tools declaradas entram como:

`mcp.example.lookup`

Por segurança, MCP tools usam risco `EXTERNAL_WRITE` por padrão e exigem aprovação.

## Remote Agents

Arquivo:

`%LOCALAPPDATA%\JarvisNext\config\remote_agents.json`

Exemplo:

```json
[
  {
    "id": "remote.research",
    "endpoint": "http://192.168.1.20:4770",
    "enabled": true,
    "token_secret": "remote_research_token"
  }
]
```

## Worker Jarvis

No outro computador:

```powershell
$env:JARVIS_WORKER_TOKEN="token-forte"
.\.venv\Scripts\python.exe -m jarvis worker --host 0.0.0.0 --port 4770
```

Para endpoints fora de localhost, token é obrigatório.

## Nodes

Registrar:

```powershell
.\.venv\Scripts\python.exe -m jarvis node-add node2 "PC 2" http://192.168.1.20:4770 --capability coding
```

Dispatch:

```powershell
.\.venv\Scripts\python.exe -m jarvis dispatch coding "Analise este problema..."
```
