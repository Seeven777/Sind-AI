# Build Validation — Jarvis Personal GPT 1.1

## Testes aprovados no ambiente de build

- Python `compileall`: OK
- `personal_gpt_test.py`: OK
- `cognitive_test.py`: OK
- `self_test.py`: OK
- `foundation_regression_test.py`: OK
- `institutional_test.py`: OK
- `autonomous_operations_test.py`: OK
- `catalog_routing_test.py`: OK
- `team_portal_test.py`: OK
- `self_awareness_test.py`: OK
- `vercel_local_test.py`: OK
- JavaScript syntax: OK
- `npm run build`: OK
- saída estática `vercel_dist/index.html`: OK

## Regressões corrigidas

### Vercel interpretava `app.py` como Python Function

- entrada desktop renomeada para `jarvis_desktop.py`;
- `run_jarvis.bat` e `run_console.bat` atualizados;
- Vercel configurada como site estático com build Node;
- runtime Python não entra na saída `vercel_dist`.

### “Quais ferramentas do SindPetshop-SP...” buscava uma fonte web irrelevante

- Self/Capability Awareness responde pelo registro real de serviços;
- teste garante que a resposta inclui Dashboard e Slack e não depende de busca genérica.

### “Veja nosso dashboard...” caía no qwen3:4b e atingia 40s

- Institutional Service Runtime identifica o Dashboard;
- Browser Agent coleta conteúdo visível;
- síntese usa FAST model;
- se o modelo falhar, existe fallback determinístico com os pontos de análise;
- nenhum timeout bruto é mostrado como única resposta.

## Validação ainda necessária no Windows real

- instalação via WinGet;
- registro `jarvis://`;
- Ollama/modelos;
- Edge/Chrome via Playwright;
- sessão autenticada de Slack/redes/sistema interno;
- leitura real do Dashboard de Insights;
- deploy real da branch atualizada na Vercel.
