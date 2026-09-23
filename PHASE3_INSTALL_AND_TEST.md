# Fase 3 — Self-Research + Verified Execution

## Instalação

Extraia este overlay na raiz do Sind-AI e execute:

```powershell
python .\apply_phase3_self_research.py
python .\run_phase3_self_research_tests.py
python -m compileall acquisition core
```

Depois:

```powershell
git diff
git status
git add .
git commit -m "feat: add autonomous self research and verified execution"
git push
```

## Teste recomendado

Use um número seu ou contato de teste:

`pesquise como faz para enviar uma mensagem utilizando o WhatsApp e tente enviar uma mensagem para 55XXXXXXXXXXX com o texto teste do Jarvis`

Fluxo esperado:

1. pesquisa fontes públicas;
2. coleta evidências;
3. sintetiza uma Skill apenas com ferramentas já permitidas;
4. valida a Skill;
5. instala localmente;
6. executa uma tentativa;
7. não afirma sucesso externo sem evidência.

## Também funciona

Pesquisa sem executar:

`pesquise como fazer para enviar uma mensagem utilizando o WhatsApp`

Aprendizado autônomo sem tentativa imediata:

`aprenda sozinho a fazer X`

## Limitação ainda existente

Esta fase não adiciona visão multimodal completa. Interfaces que não exponham bons
controles UI Automation ainda podem falhar. A fase seguinte deve adicionar
percepção visual, retries por estratégia alternativa e verificação pós-ação.
