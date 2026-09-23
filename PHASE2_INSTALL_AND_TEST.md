# Sind-AI — Personal Autonomy Phase 2

## Objetivo desta fase

A Fase 1 provou que o Jarvis consegue observar continuamente o contexto do desktop sem gravar texto digitado ou vídeo contínuo. A Fase 2 transforma esse histórico bruto em contexto operacional reutilizável.

Foram adicionados:

- episódios de trabalho;
- memória procedural persistente;
- perfis de experiência por aplicativo (Application Experts);
- recuperação de procedimentos aprendidos;
- maturidade/confiança de rotinas;
- pacote compacto de contexto operacional;
- recuperação do último contexto de trabalho quando a janela do Jarvis está em primeiro plano;
- integração opcional desse contexto ao prompt normal do Jarvis;
- novos Actions aditivos em `actions/catalog.d`;
- proteção explícita para não tratar conteúdo observado como instrução/autorização.

Nenhum banco existente é substituído. Os novos dados ficam em:

`~/JarvisData/observe/procedural.db`

O Activity Ledger da Fase 1 continua em:

`~/JarvisData/observe/activity.db`

## Instalação

1. Extraia o ZIP overlay na raiz do repositório, permitindo substituir os arquivos indicados.
2. Na raiz do repositório, execute:

```powershell
python .\apply_phase2_core_patch.py
```

O patcher altera somente três pontos pequenos de `core/agent.py`:

- monta um `personal_context` quando o observador pessoal está ativo;
- adiciona o contexto operacional ao system prompt;
- marca títulos de janela/documentos/resultados observados como dados não confiáveis, nunca como autorização.

O patcher é idempotente. Se o `core/agent.py` tiver mudado de forma incompatível, ele para em vez de tentar adivinhar.

## Validação local

```powershell
python .\run_personal_autonomy_phase2_tests.py
python -m compileall observe swarm actions
```

A suíte desta entrega possui 10 testes: os 4 testes da Fase 1 mais 6 testes novos da Fase 2.

## Testes na interface

Com o observador ativado:

```text
ative o aprendizado contínuo
```

Troque entre alguns aplicativos por alguns minutos e teste:

```text
contexto operacional
```

```text
em que eu estava trabalhando
```

```text
quais aplicativos você conhece
```

```text
o que você sabe sobre photoshop
```

```text
status do aprendizado pessoal
```

```text
quais procedimentos você aprendeu
```

Depois ensine uma rotina real:

```text
observe enquanto eu faço criar uma publicação de teste
```

Realize a rotina e finalize:

```text
terminei a demonstração
```

A rotina agora é gravada tanto como Skill quanto na nova memória procedural.

Depois consulte:

```text
quais procedimentos você aprendeu
```

ou:

```text
procure rotina publicação
```

## Teste do contexto automático

Depois de executar `apply_phase2_core_patch.py`, mantenha o observador ativo e abra um projeto/aplicativo reconhecido. Em seguida faça uma solicitação normal, sem perguntar pelo contexto.

Exemplo:

```text
preciso continuar este trabalho e revisar o que já fiz
```

O system prompt do runtime passa a receber automaticamente um pacote compacto com aplicativo atual, janela/documento provável, último episódio de trabalho, maturidade do especialista daquele aplicativo e procedimentos relacionados.

Esse contexto só é injetado automaticamente quando o observador pessoal está ativo.

## Commit

```powershell
git status
git diff

git add .
git commit -m "feat: add procedural memory and operational context"
git push
```

## Limitações intencionais desta fase

A Fase 2 ainda não observa semanticamente as ações internas do Photoshop. Ela sabe que o Photoshop está sendo usado, pode associar uma demonstração a ele e lembrar rotinas, mas o Bridge UXP/actionJSON ainda será uma fase posterior.

Também não cria automações silenciosamente a partir de um padrão de troca de aplicativos. Um padrão é evidência; uma rotina executável precisa de demonstração estruturada ou de primitivas confiáveis já existentes.

## Próxima fase recomendada

Phase 3 — Photoshop Expert + UXP Bridge:

- plugin UXP local;
- captura de eventos/actionJSON;
- leitura segura de documento/camadas;
- replay com `batchPlay`;
- sincronização desses eventos via `ObservationEngine.ingest_event()`;
- verificador de resultado;
- aprendizado de correções humanas.
