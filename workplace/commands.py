import re


def parse_workplace_command(text):
    raw = str(text or "").strip()
    low = raw.lower()

    if any(x in low for x in ("liste playbooks", "listar playbooks", "quais playbooks", "biblioteca de playbooks")):
        return {"action": "list"}

    m = re.search(r"(?:qual|quais)\s+playbook(?:s)?\s+(?:para|servem para)\s+(.+)", raw, flags=re.I)
    if m:
        return {"action": "search", "query": m.group(1).strip()}

    m = re.search(r"(?:procure|buscar|busque|pesquise)\s+(?:um\s+)?playbook\s+(?:para\s+)?(.+)", raw, flags=re.I)
    if m:
        return {"action": "search", "query": m.group(1).strip()}

    m = re.search(r"(?:use|utilize|execute|inicie|rode)\s+(?:o\s+)?playbook\s+(.+)", raw, flags=re.I)
    if m:
        return {"action": "run", "query": m.group(1).strip()}

    m = re.search(r"(?:abra|mostrar|mostre)\s+(?:o\s+)?playbook\s+(.+)", raw, flags=re.I)
    if m:
        return {"action": "get", "query": m.group(1).strip()}

    return None
