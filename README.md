# Jarvis Personal GPT 1.0 RC

Protótipo integrado de GPT pessoal local, gratuito como base, adaptável ao hardware e orientado a conversa.

## Objetivo

O Jarvis não é um catálogo de comandos. Ele é uma camada cognitiva que:
- conversa;
- mantém contexto;
- aprende preferências/correções;
- trabalha com projetos;
- lê anexos;
- pesquisa a web;
- consulta fontes públicas estruturadas;
- usa o desktop/navegador;
- aciona Actions/Workflows por trás;
- agenda/monitora rotinas;
- usa integrações autorizadas;
- registra reflexões e propostas de melhoria.

## Interface

A experiência principal possui somente:
- conversas;
- projeto atual;
- campo de chat;
- contexto opcional;
- centro de controle secundário.

Actions, Workflows, monitores e conectores continuam existindo, mas não ocupam a navegação principal.

## Novidades desta RC

- Markdown renderizado corretamente.
- Copiar, editar e regenerar mensagens.
- Painel de contexto recolhível.
- Anexos PDF/DOCX/TXT/MD/CSV/JSON/HTML indexados automaticamente.
- Projetos persistentes.
- Context Orchestrator.
- Reflection Engine.
- Skill candidates após padrões repetidos.
- Self-Improvement Queue supervisionada.
- Hardware Profiler.
- Model Router adaptável aos modelos locais instalados.
- Fontes e grounding persistidos por resposta.
- Fontes clicáveis no chat.
- Mapa de serviços cotidianos do SindPetshop-SP.
- Fast Path para abrir Instagram, Slack, Dashboard, Agenda, Site etc.
- Templates sem credenciais para APIs profissionais.

## Serviços do SindPetshop-SP mapeados

- Dashboard de Insights
- Agenda Sind
- Facebook
- LinkedIn
- Instagram
- TikTok
- Sistema interno
- Slack
- sindpetshop.org.br / WordPress

Veja `INSTITUTIONAL_SERVICES.md`.

## Dados públicos

A base inclui um broker de fontes públicas e oficiais, incluindo IBGE, MTE, DataJud, Câmara, Senado, Banco Central, Receita, dados.gov.br, compras públicas, PNCP, INEP e fontes estaduais/municipais.

## Segurança

- Nenhum token/senha real acompanha o pacote.
- Credenciais de connectors ficam no keyring do sistema.
- Ações high/critical continuam sob confirmação/Approval Queue.
- Sistema interno usa apenas sessão autenticada autorizada.
- Publicação externa não é executada silenciosamente.
- Self-improvement gera proposta; não altera o próprio código silenciosamente.

## Instalação

1. `install.bat`
2. Se necessário: `install_fast_model.bat`
3. `run_doctor.bat`
4. `run_personal_gpt_test.bat`
5. `run_cognitive_test.bat`
6. `run_self_test.bat`
7. `run_foundation_test.bat`
8. `run_model_router_test.bat`
9. `run_routing_test.bat`
10. `run_health_test.bat`
11. `run_browser_test.bat`
12. `run_jarvis.bat`

## Persistência

Dados do usuário ficam fora da pasta da release em `~/JarvisData`, evitando perda de memória ao trocar de versão.

## Limites reais

Esta RC não contém credenciais privadas, não ignora permissões dos serviços e não elimina limites físicos de hardware. A arquitetura escolhe modelos/ferramentas de acordo com o ambiente local e pode expandir por connectors, APIs públicas e Skills.


## Versão 1.1 — Vercel + runtime local

A Vercel hospeda somente um launcher estático. O aplicativo real continua no Windows. Consulte `VERCEL_DEPLOY.md`.

A 1.1 também adiciona Self/Capability Awareness para que o Jarvis responda sobre suas ferramentas a partir do estado real da instalação, e não das limitações imaginadas pelo modelo.
