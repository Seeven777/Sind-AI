# Deploy na Vercel — Jarvis Personal GPT 1.1

## O que a Vercel publica

Somente `vercel_portal/` é copiado para `vercel_dist/` pelo build. O Cognitive Core, Ollama, automação de Windows, memória e credenciais **não** são executados na Vercel.

## Correção do erro `app.py`

A antiga entrada desktop `app.py` foi renomeada para `jarvis_desktop.py`. Isso impede que a Vercel tente interpretá-la como uma Python Function. `run_jarvis.bat` e `run_console.bat` já apontam para o novo nome.

## Configuração recomendada no projeto Vercel

1. Atualize a branch `main` do GitHub com **todo o conteúdo desta release**.
2. Na Vercel, importe/abra o repositório `Seeven777/Sind-AI`.
3. Root Directory: deixe na raiz do repositório.
4. Framework Preset: **Other** se a interface pedir uma escolha.
5. O `vercel.json` já define:
   - Build Command: `node vercel_build.cjs`
   - Output Directory: `vercel_dist`
6. Não são necessárias variáveis de ambiente para o launcher.
7. Faça Redeploy. Se a Vercel estiver reaproveitando configuração antiga, confirme Build & Output Settings e faça um novo deploy sem cache.

## Fluxo do funcionário

```text
Vercel URL
   ↓
Abrir Jarvis local
   ↓
jarvis://open
   ↓
Windows abre o runtime instalado
```

Se o protocolo ainda não existir, o usuário entra na aba Instalação, baixa `Install-Jarvis.ps1` e executa:

```powershell
powershell -ExecutionPolicy Bypass -File .\Install-Jarvis.ps1
```

O instalador:
- verifica/instala Python 3.12 via WinGet quando necessário;
- verifica/instala Ollama via WinGet quando necessário;
- baixa a branch `main` do GitHub;
- cria `.venv`;
- instala `requirements.txt`;
- seleciona modelos de acordo com a RAM;
- registra `jarvis://`;
- cria atalho no Menu Iniciar;
- executa `doctor.py`;
- mantém dados persistentes em `~/JarvisData`.

## Privacidade

O portal Vercel não recebe prompts, documentos, bancos SQLite nem histórico de conversa. A execução da IA permanece local. Serviços externos acessados pelo Jarvis continuam sujeitos às permissões e políticas desses serviços.
