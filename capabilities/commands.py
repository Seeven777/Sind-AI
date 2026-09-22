import json
import re


def parse_capability_command(text):
    t = str(text).strip()
    if re.match(r"^\s*(?:quantas|mostre|liste)\s+(?:as\s+)?capacidades\b", t, re.I):
        return {"action": "stats"}
    if re.match(r"^\s*(?:liste|mostre)\s+(?:os\s+)?provedores(?:\s+de\s+capacidades)?\s*$", t, re.I):
        return {"action": "providers"}
    if re.match(r"^\s*(?:liste|mostre)\s+(?:os\s+)?grupos(?:\s+de\s+capacidades)?\s*$", t, re.I):
        return {"action": "groups"}
    m = re.match(r"^\s*(?:liste|mostre)\s+capacidades?\s+(?:do|da|de)\s+(.+?)\s*$", t, re.I)
    if m:
        return {"action": "list_filter", "value": m.group(1).strip().rstrip(".?!")}
    m = re.match(r"^\s*(?:descubra|procure)\s+(?:apis?|fontes)\s+(?:publicas?|públicas?)\s+(?:para|sobre)\s+(.+?)\s*$", t, re.I)
    if m:
        return {"action": "discover", "query": m.group(1).strip().rstrip(".?!")}

    m = re.match(r"^\s*(?:procure|busque|encontre)\s+capacidades?\s+(?:para|sobre)\s+(.+?)\s*$", t, re.I)
    if m:
        return {"action": "search", "query": m.group(1).strip().rstrip(".?!")}
    m = re.match(r"^\s*use\s+(?:a\s+)?capacidade\s+([\w.-]+)(?:\s+com\s+(\{.*\}))?\s*$", t, re.I | re.S)
    if m:
        params = {}
        if m.group(2):
            try:
                params = json.loads(m.group(2))
            except Exception:
                return {"action": "error", "error": "Parâmetros devem estar em JSON válido."}
        return {"action": "execute", "id": m.group(1), "params": params}
    return None
