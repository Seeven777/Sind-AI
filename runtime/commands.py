import re


def parse_task_command(text):
    t = str(text).strip()

    if re.match(r"^\s*(?:onde|em que lugar)\s+(?:ficam|estao|estão)\s+(?:os\s+)?(?:seus\s+)?dados\??\s*$", t, re.I):
        return {"action": "data_path"}

    if re.match(r"^\s*(?:faca|faça|crie)\s+(?:um\s+)?backup\s+(?:dos\s+)?(?:seus\s+)?dados\s*$", t, re.I):
        return {"action": "backup_data"}

    if re.match(r"^\s*(?:qual|mostre)\s+(?:a\s+)?tarefa\s+ativa\??\s*$", t, re.I):
        return {"action": "active"}

    m = re.match(r"^\s*(?:liste|mostre)\s+(?:as\s+)?(?:ultimas|últimas)?\s*(\d+)?\s*tarefas(?:\s+recentes)?\s*$", t, re.I)
    if m:
        return {"action": "recent", "limit": int(m.group(1) or 10)}

    return None
