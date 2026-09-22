# Jarvis Personal GPT 1.2 — Experience + Mobile

GPT pessoal local, gratuito como base, adaptável ao hardware e orientado a conversa.

## Princípio

O Jarvis não é um catálogo de comandos. Ele conversa, mantém contexto, aprende preferências/correções, pesquisa a web, consulta dados públicos, lê documentos, usa desktop/navegador e aciona infraestrutura interna quando necessário.

## Experiência principal

A interface foi reduzida a:

- conversas;
- projeto atual;
- campo de chat;
- contexto opcional;
- Jarvis Mobile;
- centro de controle secundário.

Actions, Workflows, monitores e conectores continuam por baixo.

## Mobile Companion

A versão 1.2 permite usar o mesmo Jarvis pelo celular na rede local:

1. abra o Jarvis no PC;
2. clique em **Jarvis Mobile**;
3. ative o acesso;
4. abra no celular o endereço exibido;
5. digite o PIN de pareamento.

O telefone é apenas a interface. Ollama, memória, arquivos e ferramentas continuam no PC.

Veja `MOBILE.md`.

## Vercel

A Vercel hospeda somente o launcher/PWA estático. O runtime Python continua local.

O portal pode ser instalado no Android/iPhone como app web e possui uma área específica para Mobile Companion.

Veja `VERCEL_DEPLOY.md`.

## Serviços SindPetshop-SP mapeados

- Dashboard de Insights
- Agenda Sind
- Facebook
- LinkedIn
- Instagram
- TikTok
- Sistema interno
- Slack
- sindpetshop.org.br / WordPress

## Instalação Windows

1. `install.bat`
2. se necessário: `install_fast_model.bat`
3. `run_doctor.bat`
4. `run_personal_gpt_test.bat`
5. `run_mobile_companion_test.bat`
6. `run_cognitive_test.bat`
7. `run_self_test.bat`
8. `run_foundation_test.bat`
9. `run_model_router_test.bat`
10. `run_routing_test.bat`
11. `run_health_test.bat`
12. `run_browser_test.bat`
13. `run_jarvis.bat`

## Persistência

Dados do usuário permanecem em `~/JarvisData`, fora da pasta da release.

## Segurança

- nenhum token/senha real acompanha o pacote;
- credenciais ficam no keyring quando aplicável;
- ações high/critical continuam sob governança;
- Mobile Companion é desligado por padrão e usa PIN/token;
- firewall mobile deve ficar restrito a redes privadas;
- não exponha a porta 8770 diretamente à internet.
