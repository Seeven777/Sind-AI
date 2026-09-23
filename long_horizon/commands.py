import re


def parse_long_horizon_command(text):
    raw = str(text or "").strip()
    low = raw.lower()

    if any(x in low for x in (
        "liste jobs", "listar jobs", "tarefas de longo prazo",
        "jobs em segundo plano", "tarefas em segundo plano",
    )):
        return {"action": "list"}

    if any(x in low for x in (
        "status dos jobs", "como estão os jobs", "como estao os jobs",
        "status das tarefas de longo prazo",
    )):
        return {"action": "stats"}

    m = re.search(r"(?:status|detalhes?|progresso)\s+(?:do\s+)?(?:job|tarefa)\s*#?\s*(\d+)", low)
    if m:
        return {"action": "get", "job_id": int(m.group(1))}

    m = re.search(r"(?:pause|pausar|pare temporariamente)\s+(?:o\s+)?(?:job|tarefa)\s*#?\s*(\d+)", low)
    if m:
        return {"action": "pause", "job_id": int(m.group(1))}

    m = re.search(r"(?:retome|retomar|continue|continuar)\s+(?:o\s+)?(?:job|tarefa)\s*#?\s*(\d+)", low)
    if m:
        return {"action": "resume", "job_id": int(m.group(1)), "force": False}

    m = re.search(r"(?:force|forçar|forcar)\s+(?:a\s+)?(?:retomada|continuação|continuacao)\s+(?:do\s+)?(?:job|tarefa)\s*#?\s*(\d+)", low)
    if m:
        return {"action": "resume", "job_id": int(m.group(1)), "force": True}

    m = re.search(r"(?:cancele|cancelar)\s+(?:o\s+)?(?:job|tarefa)\s*#?\s*(\d+)", low)
    if m:
        return {"action": "cancel", "job_id": int(m.group(1))}

    patterns = (
        r"^(?:trabalhe|trabalhar)\s+(?:nisso|nisto)\s+(?:em\s+)?segundo plano[:\s]+(.+)$",
        r"^(?:execute|executar|faça|faca)\s+(?:isso\s+)?como\s+(?:uma\s+)?tarefa\s+de\s+longo\s+prazo[:\s]+(.+)$",
        r"^(?:crie|criar)\s+(?:um\s+)?job\s+(?:para|de)\s+(.+)$",
        r"^(?:continue|continuar)\s+trabalhando\s+(?:nisso|nisto)\s+mesmo\s+se\s+demorar[:\s]+(.+)$",
    )
    for pattern in patterns:
        m = re.match(pattern, raw, flags=re.I)
        if m:
            return {
                "action": "create",
                "goal": m.group(1).strip(),
                "auto_resume": True,
            }

    return None
