# Upgrade — Jarvis Next 1.0 RC2 Agency Bridge

Base esperada: `Jarvis-Next-v1.0-RC-Full.zip` / Jarvis Next 1.0 RC.

## 1. Encerrar o Jarvis

```powershell
.\Stop-Jarvis.cmd
```

## 2. Aplicar o pacote

Opção recomendada para uma instalação já existente:

- extraia `Jarvis-Next-v1.0-RC2-Agency-Bridge-overlay.zip` diretamente sobre `C:\Users\AMD\Desktop\Sind-AI`;
- permita substituir os arquivos existentes;
- não apague `.git`, `.venv` ou `%LOCALAPPDATA%\JarvisNext`.

Também é possível usar o pacote Full, extraindo o conteúdo sobre a mesma raiz.

## 3. Atualizar o ambiente Python

```powershell
cd C:\Users\AMD\Desktop\Sind-AI
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Ou execute novamente:

```text
Setup-Jarvis-Complete.cmd
```

## 4. Confirmar o catálogo Agency

```text
Agency-Status.cmd
```

O campo `agents` deve refletir os TOMLs realmente presentes em:

```text
C:\Users\AMD\.codex\agents
```

Se o repositório continuar em:

```text
C:\Users\AMD\Desktop\agency-agents
```

Jarvis também deve detectar os runbooks NEXUS.

## 5. Testar o AgentRouter

```text
Agency-Test-Router.cmd
```

O resultado deve conter pelo menos um `agent_id` iniciado por `agency.`.

## 6. Listar runbooks

```text
Agency-Runbooks.cmd
```

## 7. Validar tudo

```text
Validate-Jarvis-Complete.cmd
```

O gate RC2 inclui uma etapa específica para Agency Agents/Codex.

## Arquitetura resultante

```text
Usuário
  -> Jarvis
      -> Intent / Mission Planner
          -> AgentRouter
              -> especialista Agency (quando relevante)
          -> agente central de entrega
          -> Reviewer
      -> Operator somente para ações reais
          -> Policy Engine
          -> ToolExecutor
          -> Observe / Act / Verify
```

As definições Agency aumentam especialização, mas não ampliam permissões de execução.
