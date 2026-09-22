# Jarvis Personal GPT 1.3 — Auto Updater + Mobile Diagnostics

## Auto Updater

- verificação automática no GitHub ao iniciar;
- verificação periódica enquanto o Jarvis permanece aberto;
- canal `main` por SHA de commit;
- canal `stable` por GitHub Releases;
- painel de atualização na UI;
- atualização com um clique;
- backup do runtime antes de substituir arquivos;
- preservação de `.venv` e `~/JarvisData`;
- `pip install -r requirements.txt` após atualização;
- validação por `compileall`;
- rollback automático quando uma etapa crítica falha;
- retenção dos três backups mais recentes.

## Correção Mobile

A 1.3 também corrige a dificuldade de acesso ao Mobile Companion:

- `Jarvis Mobile` permanece visível na sidebar;
- detecção de múltiplos IPv4 privados;
- evita depender de um único endereço possivelmente pertencente a VPN/adaptador virtual;
- diagnóstico do servidor local;
- diagnóstico do perfil de rede do Windows;
- diagnóstico da regra de Firewall;
- botão para solicitar a liberação segura no Firewall;
- lista de URLs alternativas disponíveis.

## Migração

Instalações anteriores não possuem o updater embutido. Portanto, a versão 1.3 precisa ser instalada manualmente **uma última vez** usando o `Install-Jarvis.ps1` atualizado. Depois disso, as próximas versões poderão ser aplicadas pela própria interface.
