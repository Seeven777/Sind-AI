# Arquitetura alvo incremental

```text
Input -> Intent Router -> Context/Memory -> Planner
      -> Tool Registry -> Executor -> Observer -> Verifier -> Result
                               |          |          |
                               +------- Event Bus ---+
                                            |
                                      Habitat / logs
```

## Regras

- Planejamento não é execução.
- Uma resposta de modelo não pode alterar o estado físico por si só.
- `SUCCESS` exige evidência produzida pelo verificador.
- Ausência ou ambiguidade de evidência resulta em `UNCERTAIN`, `PARTIAL` ou `FAILED`.
- Cada solicitação executável mantém ID, plano, eventos, observações, verificação e resultado.

## Migração sem quebra

1. Preservar `JarvisAgent` como fachada pública.
2. Adaptar funções atuais para um contrato `ToolDescriptor`.
3. Publicar eventos estruturados a partir de `TaskStore` e `RuntimeDiagnostics`.
4. Fazer `ui/habitat.py` traduzir o event bus para `QWebChannel` durante a transição.
5. Extrair domínios de `core/agent.py` somente depois de testes de paridade.

## Contratos alvo

```python
class ToolDescriptor:
    name: str
    description: str
    parameters: dict
    risk_level: str
    execute: Callable
    verify: Callable

class ExecutionResult:
    status: Literal["SUCCESS", "FAILED", "PARTIAL", "UNCERTAIN"]
    output: object
    evidence: list[object]
    error: str | None
```

O primeiro passo não é substituir as ferramentas existentes, mas envolvê-las nesses contratos.

