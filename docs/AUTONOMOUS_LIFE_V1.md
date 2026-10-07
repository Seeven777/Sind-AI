# Jarvis — Autonomous Life v1

Esta versão adiciona um ciclo de vida persistente ao Jarvis sem transformar aprendizado autônomo em autorização irrestrita.

## O que acontece enquanto o Jarvis está ligado

O processo de background roda no mesmo runtime do HQ. Em intervalos configuráveis ele pode:

- atualizar o briefing diário;
- escolher sozinho um assunto de qualquer área e pesquisá-lo;
- registrar descobertas na memória persistente;
- classificar sozinho se uma descoberta é `ambient`, `important` ou `critical`;
- solicitar atenção por UI/voz quando julgar necessário;
- inspecionar a própria saúde e propor uma melhoria pequena e verificável;
- depois da aprovação humana, transformar a melhoria em uma missão supervisionada de implementação/revisão.

O Jarvis não declara uma autoalteração como aplicada sem evidência. Nesta versão, a missão aprovada prepara e revisa a implementação; alterações do core continuam sujeitas ao gate humano.

## Briefing de início de rotina

A Home reúne:

- previsão do tempo do local configurado;
- responsabilidades/prioridades já conhecidas pelo runtime;
- últimas notícias pesquisadas;
- descobertas autônomas recentes;
- melhorias propostas pelo próprio Jarvis.

Quando voz está habilitada, o Companion pode emitir um cumprimento matinal curto uma vez ao dia e dizer “Senhor” para uma nova atenção importante/crítica.

## Interface viva

`jarvis-core.js` implementa um núcleo WebGL2 original, com fallback Canvas 2D. O núcleo reage a estados reais como `IDLE`, `LISTENING`, `THINKING`, `RESEARCHING`, `EXECUTING`, `VERIFYING`, `SPEAKING`, `ATTENTION` e `ERROR`.

O Office 3D ganhou:

- núcleo de partículas;
- fluxos de dados entre departamentos e Command Core;
- pulsos de handoff baseados na timeline real;
- energia/iluminação de salas orientada por atividade;
- presença visual `ASSISTING` separada de `EXECUTING`;
- movimentação sutil de agentes e telemetria visual.

## Inicialização com o Windows

No PowerShell, a partir da raiz do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install_windows_startup.ps1
```

Isso cria a tarefa `JarvisNext` para iniciar o Companion em segundo plano no logon. Para remover:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\uninstall_windows_startup.ps1
```

## Requisitos para autonomia completa

A pesquisa autônoma precisa de acesso à internet e de um modelo configurado no Model Mesh. Se uma fonte/modelo estiver indisponível, o loop registra a falha e continua nas próximas iterações em vez de derrubar o Jarvis.
