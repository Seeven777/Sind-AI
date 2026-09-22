import re


def _clean_name(value):
    return str(value).strip().strip('"').strip("'").rstrip(" .!?;,:")


def parse_skill_command(text):
    t = str(text).strip()

    # "Salve as últimas 2 ações como skill rotina teste."
    m = re.match(
        r"^\s*salve\s+as\s+[uú]ltimas\s+(\d+)\s+a[cç][oõ]es\s+como\s+skill\s+(.+?)\s*$",
        t,
        flags=re.I,
    )
    if m:
        return {
            "action": "save_recent",
            "count": int(m.group(1)),
            "name": _clean_name(m.group(2)),
        }

    # "Salve a última ação como skill abrir bloco."
    m = re.match(
        r"^\s*salve\s+a\s+[uú]ltima\s+a[cç][aã]o\s+como\s+skill\s+(.+?)\s*$",
        t,
        flags=re.I,
    )
    if m:
        return {
            "action": "save_recent",
            "count": 1,
            "name": _clean_name(m.group(1)),
        }

    # "Execute a skill rotina teste com {"mes":"setembro"}."
    m = re.match(
        r"^\s*(?:execute|rode|inicie)\s+(?:a\s+)?skill\s+(.+?)\s+com\s+(\{.*\})\s*$",
        t,
        flags=re.I | re.S,
    )
    if m:
        import json
        try:
            values = json.loads(m.group(2))
        except Exception:
            return {"action": "error", "error": "Entradas da skill devem estar em JSON válido."}
        return {
            "action": "run",
            "name": _clean_name(m.group(1)),
            "inputs": values,
        }

    # "Execute a skill rotina teste."
    m = re.match(
        r"^\s*(?:execute|rode|inicie)\s+(?:a\s+)?skill\s+(.+?)\s*$",
        t,
        flags=re.I,
    )
    if m:
        return {
            "action": "run",
            "name": _clean_name(m.group(1)),
        }

    # "Exclua a skill rotina teste."
    m = re.match(
        r"^\s*(?:exclua|apague|remova)\s+(?:a\s+)?skill\s+(.+?)\s*$",
        t,
        flags=re.I,
    )
    if m:
        return {
            "action": "delete",
            "name": _clean_name(m.group(1)),
        }

    # "Liste suas skills."
    if re.match(
        r"^\s*(?:liste|mostre|quais\s+s[aã]o)\s+(?:as\s+)?(?:suas\s+)?skills\b",
        t,
        flags=re.I,
    ):
        return {"action": "list"}

    # "Mostre as últimas 5 ações."
    m = re.match(
        r"^\s*(?:mostre|liste)\s+as\s+[uú]ltimas\s+(\d+)\s+a[cç][oõ]es\b",
        t,
        flags=re.I,
    )
    if m:
        return {
            "action": "recent_actions",
            "count": int(m.group(1)),
        }


    if re.match(r"^\s*(?:sugira|sugestao|sugestão|encontre)\s+(?:novas\s+)?skills\b", t, flags=re.I):
        return {"action": "suggest_patterns"}

    return None
