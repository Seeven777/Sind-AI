# Jarvis Cinematic Upgrade — Overlay

Base auditada: `Seeven777/Sind-AI` (`main`, commit observado `a5366cc`).

## O que este overlay altera

### 1. Interface / orb / widgets
- substitui `ui/web/orb.js` por uma orb procedural mais viva e reativa;
- adiciona `ui/web/jarvis-cinematic-v2.css`;
- estados visuais: idle, listening, thinking, planning, executing, observing, verifying, speaking, success e error;
- widgets contextuais flutuantes para atividade, projeto, modelo, hardware e memória;
- rail visual do fluxo da IA;
- sem biometria, face scan ou etapa inicial de identificação;
- mantém Canvas 2D e qualidade adaptativa para Radeon integrada.

### 2. Arrastar entre monitores
O bridge Python já possuía `beginMove()` -> `QWindow.startSystemMove()`, mas a interface web não acionava esse método.
O novo `orb.js` liga as áreas `.drag-zone` ao movimento nativo da janela. Isso permite arrastar a janela frameless normalmente entre monitores no Windows.

### 3. Voz ElevenLabs
Voz fixa solicitada: `2CECaLAGTS5NRGxgbcxr`.
A voz nativa do Windows deixa de ser fallback automático.

A chave fica fora do Git em:
`%USERPROFILE%\JarvisData\secrets\elevenlabs_api_key.txt`

Depois de copiar o overlay, execute uma vez:
`Configurar-Voz-ElevenLabs.cmd`

A ElevenLabs exige uma chave válida e o uso está sujeito ao plano/quota da sua conta.

### 4. Vercel
O `vercel.json` força o projeto para `framework: null` (Framework Preset "Other"), executa `node vercel_build.cjs` e publica `vercel_dist`.
Isso evita que o `pyproject.toml` faça a Vercel procurar um entrypoint Python para o launcher estático.

### 5. Limpeza segura
`LIMPAR-PROJETO-SEGURO.cmd` somente gera relatório.
Ele nunca remove automaticamente:
- `.git`;
- `.venv` / `.venv-openjarvis`;
- `JarvisData`;
- bancos SQLite;
- segredos;
- código-fonte;
- arquivos rastreados pelo Git.

Para remover caches não rastreados depois de revisar o relatório:
`python scripts\cleanup_project.py --apply`

## Instalação
1. Faça backup/commit do estado atual.
2. Extraia este ZIP na raiz do `Sind-AI`, aceitando substituir os arquivos existentes.
3. Execute `Configurar-Voz-ElevenLabs.cmd` se quiser a voz neural.
4. Inicie pelo `Iniciar-Jarvis-Integrado.cmd` normalmente.
5. Teste a janela em ambos os monitores segurando a área superior vazia e arrastando.
6. Faça um novo deploy na Vercel a partir da branch que contém este `vercel.json`.

## Testes
O ZIP foi validado com `run_upgrade_tests.py`, `py_compile` e `node --check` para os arquivos alterados.
