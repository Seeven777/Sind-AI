# Atualização visual v2

## O que mudou

- Tema escuro como padrão, seguindo a linguagem das ferramentas do SindPetshop-SP; botão de alternância para tema claro.
- Tela inicial com chamada principal, próximos prazos, atalhos de criação e diário, visão das etapas e tarefas em foco.
- Cores, tipografia, cartões, barra lateral, Kanban, calendário, relatórios, formulários e tela de entrada harmonizados.
- Links de acesso rápido para Sind AI, Agenda Sind e SindApp.
- URL de fallback dos insights atualizada para `https://dashbord-de-ensigths.vercel.app/`.

## Publicação sobre o projeto atual

Substitua os arquivos correspondentes no mesmo repositório Git e faça commit/push. A Vercel fará uma nova build se o Git estiver conectado. Preserve suas variáveis de ambiente e o banco Supabase existentes. Nenhuma migração SQL é necessária.

Se `VITE_INSIGHTS_URL` já está configurada na Vercel com o endereço antigo, atualize a variável para o endereço que deseja usar; ela tem prioridade sobre o fallback do código. Uma mudança de variável na Vercel só entra após novo deploy.

## Verificação

`npm run build` concluído. A interface foi implementada em código e não foi validada visualmente dentro do ambiente autenticado de produção da equipe.
