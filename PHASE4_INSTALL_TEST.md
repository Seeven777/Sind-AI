# Fase 4 — Real Execution Runtime

## Base e formato de instalação

Este overlay foi preparado a partir dos bytes de `JARVIS(2).zip` fornecidos nesta solicitação. O HEAD encontrado é `0c954b2b7a1730e62d04092f1c714949b2601330`. O ZIP de origem já tinha alterações locais em `core/agent.py` e `cognitive/answer_engine.py`; elas foram preservadas como base, sem reset para o conteúdo do commit.

O desenvolvimento foi feito na branch local `phase4-real-execution-overlay`. A referência `main` permanece no commit original. Não houve commit, push, merge ou alteração remota.

O ZIP contém somente arquivos novos/alterados, com caminhos relativos à raiz do projeto. Não há uma pasta `JARVIS/` adicional dentro dele. Não contém `.git`, `.venv`, configuração do usuário, banco de dados, credenciais, histórico de conversas ou dependências.

1. Feche o Jarvis, inclusive a instância da bandeja.
2. Faça uma cópia da pasta atual ou preserve o ZIP original para rollback.
3. Abra o PowerShell na raiz do projeto, onde estão `core`, `runtime` e `jarvis_desktop.py`.
4. Confira a base e crie uma branch para a instalação:

```powershell
git rev-parse --short HEAD
# Esperado: 0c954b2
git switch -c phase4-real-execution
Expand-Archive -LiteralPath "$HOME\Downloads\Sind-AI-Phase4-Real-Execution-overlay.zip" -DestinationPath . -Force
.\.venv\Scripts\python.exe .\run_phase4_tests.py
```

Se a branch já existir, use outro nome. Não use `git reset --hard`: a base fornecida inclui alterações locais. Se estiver em outro commit, aplique primeiro em uma cópia da base correta. O overlay substitui arquivos completos e não faz merge de alterações posteriores.

Depois dos testes, abra o Jarvis pelo seu atalho habitual. Nenhuma dependência nova foi adicionada: o adaptador usa o `pywinauto` já presente em `requirements.txt`, UI Automation do Windows e biblioteca padrão. Não usa APIs pagas, modelos remotos ou GPU.

## O que mudou

- Classificação determinística de pedidos informativos, rascunhos, simulações e pedidos executáveis. `Como enviar no WhatsApp?` não autoriza envio; `Envie no WhatsApp para Maria Silva: Olá!` é executável.
- Pedidos executáveis recebem ferramentas desktop automaticamente, com prioridade para não desaparecerem no corte dos schemas. Não entram no fluxo leve de conversa nem no Swarm como substituto de execução.
- Se o modelo apenas narrar uma ação sem chamar ferramenta, o loop solicita execução novamente dentro do limite configurado. Uma resposta textual não comprova conclusão.
- Sessão de execução isolada por thread. O registro separa `tool_execution` e `goal_verification`. A barreira de resposta roda depois da normalização de idioma, antes de salvar conversa e aprendizado.
- Retornos genéricos `ok: true`, planos, leituras e cliques não comprovam um objetivo físico. Objetivos não verificados não são aprendidos como tarefas concluídas. Não há encaminhamento automático de pedidos executáveis para jobs que poderiam repetir efeitos.
- Digitação exige um campo editável, visível, habilitado e não sensível. Seleção por nome/automation ID, foco inequívoco ou papel semântico. Ambiguidade causa falha; não há escolha do primeiro campo nem colagem em foco desconhecido. O valor é relido depois da escrita.
- O executor WhatsApp é determinístico e usa UIA real. Não pede ao modelo para inventar contato, texto, seletores ou resultados.
- Abertura do WhatsApp não usa fallback silencioso para WhatsApp Web.

### Ciclo WhatsApp

1. Observar o desktop e localizar a janela do processo nativo `WhatsApp.exe`; se necessário, solicitar abertura pelo protocolo `whatsapp:`.
2. Observar novamente e localizar o campo de pesquisa pela semântica UIA.
3. Preencher a pesquisa e reler seu valor.
4. Exigir um único contato com nome correspondente, preservando acentos. Homônimos não são escolhidos automaticamente.
5. Abrir a conversa e verificar o nome no cabeçalho da área da conversa.
6. Localizar o compositor e ler o rascunho. Rascunhos existentes são preservados e interrompem a operação.
7. Aplicar a confirmação já configurada em `deep_access.confirm_risky_controls`. Por padrão, a confirmação é obrigatória. Clientes sem callback não passam por essa confirmação e o envio é bloqueado.
8. Reobservar após a confirmação, inserir o texto literal usando UIA ValuePattern e reler seu valor integral.
9. Revalidar a conversa, o texto e o botão Enviar. Invocar o botão uma única vez, sem fallback por Enter ou clique após erro.
10. Observar até encontrar uma nova mensagem de saída com o texto exato, identidade UIA nova e estado explícito de enviada/entregue/lida, na mesma conversa, com compositor vazio. A quantidade de mensagens correspondentes deve aumentar em relação à observação anterior.

Uma mensagem antiga, recebida, pendente, um rascunho ou apenas um runtime ID diferente não validam o envio. A confirmação significa evidência de envio na interface; não constitui confirmação independente do servidor nem de leitura pelo destinatário.

Se a invocação de Enviar tiver sido tentada e a verificação não for possível, o retorno é **Envio incerto**. Não há reenvio automático, inclusive se a UIA gerar exceção após a invocação. Confira a conversa antes de solicitar uma nova tentativa. Uma nova solicitação explícita é uma nova operação; não existe deduplicação persistente entre reinícios.

## Teste manual no Windows

Use o WhatsApp Desktop instalado e autenticado, com sessão do Windows desbloqueada. Jarvis e WhatsApp devem ter o mesmo nível de privilégio. Para o primeiro envio real, use sua conversa de teste e substitua o nome abaixo pelo nome único que aparece na interface.

Teste informativo, sem envio:

```text
Como enviar uma mensagem pelo WhatsApp Desktop?
```

Teste de abertura:

```text
Abra o WhatsApp
```

Teste de envio literal:

```text
Envie no WhatsApp para CONTATO DE TESTE: Teste Fase 4 — execução real.
```

Também são aceitas estas formas:

```text
Envie "Olá, tudo bem?" para CONTATO DE TESTE no WhatsApp
Abra o WhatsApp e envie para CONTATO DE TESTE a mensagem "Teste com acentuação!"
```

Use a forma com dois-pontos para mensagens que contenham aspas. Sem contato/texto inequívocos, Jarvis solicita os dados, sem enviar. Referências implícitas como “mande aquilo para ele” não são resolvidas automaticamente. Não interaja com mouse/teclado durante a sequência; se o cabeçalho ou rascunho mudar, o executor interrompe a operação.

Confira também:

- Contato inexistente: falha, nenhuma mensagem enviada.
- Contatos duplicados: falha por ambiguidade.
- Negar a confirmação: nenhuma mensagem digitada ou enviada; a pesquisa/conversa pode ter sido aberta.
- Rascunho existente: preservado, envio bloqueado.
- Texto inserido, mas UIA sem evidência de saída: nunca exibir sucesso. Após tentativa de envio, relatar incerteza e não repetir.
- Pedido genérico `digite "Olá, mundo!"`: exigir destino inequívoco e reler o texto, preservando pontuação. Isso não significa que uma mensagem foi enviada.

Inspeção UIA somente leitura, sem abrir aplicativo nem enviar mensagens:

```powershell
.\.venv\Scripts\python.exe .\run_phase4_tests.py --probe
```

Abra o WhatsApp manualmente antes do probe. Ele mostra rótulos/IDs e propriedades dos campos expostos, sem listar histórico ou valores de rascunhos. Rótulos podem conter dados pessoais da interface; revise a saída antes de compartilhar.

## Compatibilidade e limites concretos

O adaptador reconhece rótulos comuns em português e inglês. Exige UIA ValuePattern para leitura/escrita de campos, um cabeçalho inequívoco, resultados de contato acessíveis e mensagens de saída com indicação explícita de estado. Versões que não exponham esses elementos, árvores UIA incompletas, diálogos extras, janelas bloqueadas ou mudanças no layout podem produzir falha/incerteza. Não há fallback por OCR, coordenadas fixas, envio cego ou navegador.

O runtime fornece observação antes/depois de ações desktop, mas **não implementa um verificador universal para qualquer objetivo**. Nesta fase, a conclusão integral é implementada para envio WhatsApp explícito, abertura simples de aplicativo nativo suportado e digitação literal simples. Outros objetivos, sobretudo compostos, podem executar etapas e terminar como não verificados. É deliberado: uma ferramenta bem-sucedida não certifica toda a solicitação. Extensões devem adicionar pós-condições específicas, não aceitar texto do modelo como evidência.

Os eventos compactos `whatsapp_observe`, `whatsapp_act` e `whatsapp_verify` usam o TaskStore existente. Não exportam o histórico completo da conversa. Estado incerto é registrado como tarefa falha, com `execution_status: uncertain` nos metadados da resposta, porque o esquema existente não exige um novo status de banco.

## Validação executada na preparação

- Python 3.12: compilação/sintaxe dos **207 arquivos Python do projeto**, excluindo dependências, dados e caches.
- **38 testes da Fase 4**, offline, com UI simulada e métodos reais do agente carregados sem dependências Windows.
- **10 testes das Fases 1/2** pelo runner existente.
- **5 testes da Fase 3** pelo runner existente.
- Conferência de paths/conteúdo do overlay contra o ZIP original; nenhum arquivo inalterado ou de dados é incluído.
- A referência `main` permaneceu em `0c954b2`.

Os testes da Fase 4 cobrem roteamento, preservação de texto, seleção segura, bloqueio de destinatário/texto inventado, resposta falsa do modelo, separação execução/verificação, duplicidade, falha antes/depois de envio, cancelamento, mudança de conversa, negação, mensagem antiga/recebida/pendente e bloqueio de repetição na mesma sessão.

**O ambiente de preparação é Linux: não houve envio real, teste de login nem validação ponta a ponta do WhatsApp Desktop no Windows.** Os testes automatizados não substituem o teste manual acima. O programa não afirma que um envio real ocorreu durante a preparação deste pacote.

## Arquivos do overlay

Alterados: `access/commands.py`, `access/controller.py`, `cognitive/answer_engine.py`, `core/agent.py`, `runtime/verifier.py`, `tools/apps.py`.

Novos: `runtime/phase4/__init__.py`, `runtime/phase4/intent.py`, `runtime/phase4/controls.py`, `runtime/phase4/runtime.py`, `runtime/phase4/whatsapp.py`, `runtime/phase4/whatsapp_uia.py`, `tests/test_phase4_real_execution.py`, `run_phase4_tests.py`, `PHASE4_INSTALL_TEST.md`.

Para rollback, feche o Jarvis e restaure os seis arquivos alterados a partir da sua cópia original; remova os nove arquivos novos se desejar remover completamente a Fase 4. Não substitua a pasta de dados.
