# Jarvis Personal GPT 1.7 — Long-Horizon + Institutional Workspace

## Long-Horizon Autonomy

A 1.7 adiciona jobs persistentes para tarefas que podem levar muitas etapas ou sobreviver ao reinício do Jarvis.

- checkpoints entre etapas;
- retomada automática de etapas seguras após reinício;
- bloqueio de retomada automática quando a etapa interrompida podia causar efeito externo;
- retries controlados;
- pausa no próximo checkpoint;
- cancelamento persistente;
- handoff automático quando uma tarefa normal atinge o limite estrutural de autonomia;
- painel de jobs na área de Atividade.

Exemplos:

`Trabalhe nisso em segundo plano: analise nosso planejamento de outubro e monte a estratégia completa.`

`Status do job #3.`

`Pause o job #3.`

`Retome o job #3.`

## Institutional Workspace

Todas as nove ferramentas cotidianas fornecidas pelo SindPetshop-SP agora possuem abas persistentes no Jarvis Desktop:

- Insights SindPetshop-SP;
- Agenda Sind;
- Facebook;
- LinkedIn;
- Instagram;
- TikTok;
- Sistema interno;
- Slack;
- Site / WordPress.

As abas usam um perfil persistente do Qt WebEngine em `~/JarvisData/browser_profile/institutional_tabs`, portanto uma sessão autenticada pode continuar disponível entre execuções conforme o serviço permitir.

As páginas são carregadas sob demanda para não deixar nove sites pesados consumindo recursos na inicialização.

## Jarvis usando as próprias abas

O Agent Runtime agora prefere o serviço institucional correto antes de abrir Google ou um navegador externo.

Operações internas disponíveis:

- `open`;
- `inspect`;
- `reload`;
- `fill`;
- `click`.

Cliques com rótulos sensíveis como publicar, enviar, excluir, salvar, confirmar, cadastrar, comprar ou pagar continuam sujeitos à confirmação do usuário.

O Browser Agent externo permanece como fallback.

## Exclusão de conversas

O histórico do Desktop agora possui um botão `×` por conversa.

Ao excluir:

- mensagens da conversa são removidas;
- índice FTS daquela conversa é removido;
- vínculo com projetos é removido;
- anexos exclusivos da conversa são removidos da Knowledge Base;
- anexos que também pertencem a um projeto são preservados.

A mesma exclusão foi adicionada ao Mobile Companion.

## Observação

Memórias, lições e competências já aprendidas pelo Jarvis não são automaticamente apagadas quando uma conversa é excluída. Elas são estruturas persistentes distintas do histórico de chat.
