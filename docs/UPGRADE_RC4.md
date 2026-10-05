# Upgrade para Jarvis Next RC4

1. Pare o Jarvis.
2. Extraia o Full RC4 sobre a pasta atual, preservando `.git`, `.venv` e os dados em `%LOCALAPPDATA%\\JarvisNext`.
3. Reinstale o pacote editável.
4. Execute a suíte completa.
5. Inicie o Companion.

Comandos:

```powershell
cd C:\Users\AMD\Desktop\Sind-AI
.\Stop-Jarvis.cmd
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\Validate-Jarvis-Complete.cmd
.\Start-Jarvis.cmd
```

Para a experiência em janela:

```powershell
.\Start-Jarvis-Desktop.cmd
```

HQ:

`http://127.0.0.1:4760/hq`

HQ clássico/fallback:

`http://127.0.0.1:4760/hq-classic`
