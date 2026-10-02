# Google — Gmail e Calendar

## Escopo

Os connectors Google desta versão são read-only:

- Gmail: `gmail.readonly`
- Calendar: `calendar.readonly`

## 1. Criar OAuth Client

No Google Cloud, crie um OAuth Client para aplicação Desktop.

Baixe o JSON.

## 2. Salvar

Renomeie para:

`google_client.json`

Salve em:

`%LOCALAPPDATA%\JarvisNext\config\google_client.json`

Nunca envie esse arquivo ao Git.

## 3. Autorizar

Execute:

`Connect-Google.cmd`

ou:

```powershell
.\.venv\Scripts\python.exe -m jarvis google-auth
```

O navegador abrirá a autorização.

## 4. Token

O token fica em:

`%LOCALAPPDATA%\JarvisNext\secrets\google_token.bin`

No Windows ele é protegido por DPAPI.

## 5. Sincronizar

`Sync-Jarvis.cmd`

ou:

```powershell
.\.venv\Scripts\python.exe -m jarvis sync
```

## 6. Desconectar

```powershell
.\.venv\Scripts\python.exe -m jarvis google-disconnect
```

O Jarvis continua funcionando normalmente mesmo sem Google configurado.
