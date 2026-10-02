# Sistema de ferramentas

## Inventário atual

- Desktop/Windows: `tools/apps.py`, `tools/windows.py`, `tools/screen.py`, `runtime/phase4/`.
- Arquivos: `tools/files.py` com raízes permitidas.
- Navegador: `tools/browser.py`, `browser_agent/`.
- Clipboard: `tools/clipboard.py`.
- WhatsApp: executores e verificadores em `runtime/phase4/`.
- Pesquisa e dados públicos: `web_search/`, `research/`, `public_data/`.
- Ações, workflows e capabilities: hubs próprios em seus diretórios.

## Política de execução

Ferramentas mutáveis devem seguir `intent -> plan -> observe -> act -> observe -> verify -> result`. O modelo nunca é a fonte de verdade do sucesso.

## Lacuna atual

Os módulos possuem interfaces heterogêneas. A próxima migração deve registrar metadados, risco e função de verificação em um catálogo único, usando adaptadores para não alterar implementações estáveis.

