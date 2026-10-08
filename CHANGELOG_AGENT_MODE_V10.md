# Jarvis Agent Mode v10 — Evolution Lab

## Objetivo
Transformar a auto-melhoria de uma simples proposta textual em um ciclo real, supervisionado e verificável.

## Novo ciclo
1. Jarvis detecta uma oportunidade de melhoria.
2. Developer prepara uma proposta e Reviewer revisa.
3. O usuário aprova a tentativa de implementação.
4. Jarvis copia o projeto para um sandbox isolado em `JarvisNext/evolution/<proposal_id>/candidate`.
5. Developer produz patches mínimos somente para `src/jarvis/` ou `tests/`.
6. Jarvis aplica os patches apenas no sandbox.
7. Executa `compileall` e a suíte completa de `pytest`.
8. Se falhar, Developer recebe o diagnóstico e ganha uma tentativa automática de reparo.
9. Somente uma candidata verde é apresentada para aprovação final.
10. Ao aprovar a promoção, Jarvis cria backup dos arquivos reais, aplica a candidata e roda a suíte novamente.
11. Se a validação pós-promoção falhar, os arquivos são restaurados automaticamente.
12. A atualização só entra em execução após reiniciar o Jarvis.

## Segurança
- sem escrita silenciosa no core;
- duas aprovações humanas: implementar em sandbox e promover;
- paths restritos a código/testes;
- traversal e arquivos sensíveis bloqueados;
- no máximo 3 arquivos e 8 substituições por arquivo por tentativa;
- backup obrigatório antes da promoção;
- rollback automático em falha;
- rollback manual preservado pelo serviço.

## Interface
O painel de atenção distingue:
- `Aprovar melhoria` → autoriza apenas o sandbox;
- `Revisar e aplicar` → candidata já testada e pronta para promoção.

## Validação desta release
- 132 testes automatizados passando;
- release self-test passando;
- Python compile check passando;
- JavaScript syntax check passando.
