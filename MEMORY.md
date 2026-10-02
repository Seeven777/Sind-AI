# Memória

## Camadas existentes

- Memória explícita e aliases: `MemoryStore`.
- Histórico de conversa: `ConversationStore`.
- Memória semântica opcional: `SemanticMemory`.
- Projetos e notas: `ProjectStore`.
- Lições e reflexões: `LearningJournal` e `ReflectionEngine`.
- Histórico operacional: `TaskStore` e `RuntimeDiagnostics`.

## Persistência

O diretório padrão é `%USERPROFILE%/JarvisData`. Isso permite atualizar o código sem apagar memória, projetos ou histórico.

## Recuperação contextual

`ContextOrchestrator` deve continuar selecionando subconjuntos relevantes. Não se deve enviar toda a memória a cada chamada. Aliases como “pasta teste” pertencem à memória explícita e precisam ser resolvidos antes da seleção de ferramenta.

## Cuidados

- Não misturar evidência de execução com lembranças do modelo.
- Registrar origem e data de memórias inferidas.
- Permitir inspeção e exclusão pelo usuário.
- Tratar memória semântica como recuperação, não como autorização para executar ações.

