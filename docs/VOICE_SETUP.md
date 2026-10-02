# Voz local

A arquitetura de voz não é obrigatória para o Jarvis funcionar.

## STT — whisper.cpp

Configure:

- `JARVIS_WHISPER_CPP`
- `JARVIS_WHISPER_MODEL`

Exemplo:

```powershell
$env:JARVIS_WHISPER_CPP="C:\AI\whisper\whisper-cli.exe"
$env:JARVIS_WHISPER_MODEL="C:\AI\whisper\models\ggml-small.bin"
```

## TTS — Piper

Configure:

- `JARVIS_PIPER`
- `JARVIS_PIPER_MODEL`

Exemplo:

```powershell
$env:JARVIS_PIPER="C:\AI\piper\piper.exe"
$env:JARVIS_PIPER_MODEL="C:\AI\piper\pt_BR-model.onnx"
```

## Diagnóstico

```powershell
.\.venv\Scripts\python.exe -m jarvis voice-doctor
```

Se voz estiver `unconfigured`, Companion, agentes, tarefas e HQ continuam funcionando.
