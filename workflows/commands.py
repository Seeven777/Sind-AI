import json
import re


def _clean(value):
    return str(value or "").strip().strip("\"'").rstrip(" .!?")


def parse_workflow_command(text):
    t = str(text).strip()

    if re.match(
        r"^\s*(?:(?:quantos|quantas)\s+(?:os\s+)?workflows|"
        r"(?:liste|mostre)\s+(?:os\s+)?workflows)\s*[.!?]*\s*$",
        t, re.I,
    ):
        return {"action": "stats"}

    m = re.match(
        r"^\s*(?:procure|busque|encontre|pesquise)\s+"
        r"(?:os?\s+)?workflows?\s+(?:para|sobre|de)\s+(.+?)\s*[.!?]*\s*$",
        t, re.I,
    )
    if m:
        return {"action": "search", "query": _clean(m.group(1))}

    m = re.match(
        r"^\s*(?:mostre|liste)\s+(?:os\s+)?workflows?\s+"
        r"(?:(?:relacionados?|relacionadas?)\s+(?:a|ao|à|aos|às|com)|"
        r"(?:dispon[ií]veis?)\s+(?:para|sobre)|(?:para|sobre))\s+(.+?)\s*[.!?]*\s*$",
        t, re.I,
    )
    if m:
        return {"action": "search", "query": _clean(m.group(1))}

    m = re.match(
        r"^\s*quais\s+workflows?\s+(?:existem\s+)?(?:para|sobre|de)\s+(.+?)\s*[.!?]*\s*$",
        t, re.I,
    )
    if m:
        return {"action": "search", "query": _clean(m.group(1))}

    m = re.match(
        r"^\s*(?:execute|rode|use)\s+(?:o\s+)?workflow\s+"
        r"([\w.-]+)(?:\s+com\s+(\{.*\}))?\s*$",
        t, re.I | re.S,
    )
    if m:
        params = {}
        if m.group(2):
            try:
                params = json.loads(m.group(2))
            except Exception:
                return {"action": "error", "error": "Parâmetros do workflow devem ser JSON válido."}
        return {"action": "execute", "id": m.group(1), "params": params}

    return None
