# Ecossistema cotidiano do SindPetshop-SP no Jarvis

Esta versão trata os serviços abaixo como **extensões do ambiente de trabalho** e não como abas permanentes da interface.

## Serviços mapeados

| Serviço | Uso no Jarvis | Acesso inicial |
|---|---|---|
| Insights SindPetshop-SP | leitura de desempenho, contexto editorial e monitoramento | web/browser |
| Agenda Sind | agenda/rotina operacional | sessão de navegador autorizada |
| Facebook | presença social e revisão de conteúdo | browser público/autenticado |
| LinkedIn | presença institucional e publicação futura | browser + API quando autorizada |
| Instagram | conteúdo, tendências próprias e métricas | browser + dashboard + API futura |
| TikTok | conteúdo curto e publicação futura | browser + API futura |
| Sistema interno | operação cotidiana autorizada | browser privado autenticado |
| Slack | comunicação interna e alertas | browser; API/webhook opcional |
| sindpetshop.org.br | conhecimento público, SEO e WordPress | web + REST autorizado |

## Princípio de funcionamento

O usuário não precisa escolher a ferramenta.

Exemplos:

`Veja como está o desempenho recente e sugira um tema.`

Jarvis pode resolver como:

1. consultar o dashboard;
2. usar contexto das publicações e projeto atual;
3. pesquisar assunto público se necessário;
4. responder com uma proposta.

`Abra o Instagram do sindicato.`

Jarvis usa o Fast Path do mapa institucional.

`Prepare uma matéria e salve como rascunho no site.`

Jarvis pode:

1. pesquisar;
2. consultar CCT/knowledge;
3. criar texto;
4. solicitar aprovação se necessário;
5. usar WordPress REST em modo rascunho.

## Segurança

- Nenhum login/senha/token está incluído nesta release.
- Browser usa somente sessões que o usuário autenticou.
- O sistema interno não é varrido automaticamente.
- Slack/Meta/LinkedIn/TikTok usam menor privilégio quando APIs forem conectadas.
- Publicação externa deve continuar sob Approval Queue quando classificada como high/critical.
- Segredos ficam no keyring do sistema.

## Integrações futuras já preparadas

`data/connector_templates.json` contém modelos sem credenciais para:

- WordPress REST;
- Slack Web API / Incoming Webhook;
- LinkedIn Posts API;
- TikTok Content Posting API;
- Meta / Instagram Professional API.

A camada genérica `ConnectorGateway` já existente pode receber esses acessos depois da autorização, sem redesenhar o Jarvis.
