# Instalação — Jarvis Next Phase 0

## Antes

A pasta deve ser:

`C:\Users\AMD\Desktop\Sind-AI`

Extraia **o conteúdo deste ZIP diretamente nela**.

É normal existir `.git`.

## Instalar

Clique duas vezes em:

`Setup-Jarvis-Phase0.cmd`

O instalador:

1. instala Git se necessário;
2. instala Python 3.13 se necessário;
3. cria `.venv`;
4. instala somente as dependências da Foundation;
5. executa os testes;
6. executa smoke boot;
7. executa stress test.

Não instala:

- Ollama
- Node
- PySide
- modelos
- ElevenLabs
- Playwright
- Docker
- LangChain

## Validar novamente

`Validate-Phase0.cmd`

## Resultado esperado

- 12 testes ou mais: PASS
- smoke boot: HEALTHY
- 50 boots: PASS
- 10.000 tasks: PASS
- 100.000 eventos: PASS

Se houver falha, não prossiga para a Phase 1.
