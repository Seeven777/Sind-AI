import json
import re


def _clean_query(value):
    return str(value or "").strip().strip("\"'").rstrip(" .!?")


def parse_action_command(text):
    t = str(text).strip()

    if re.match(
        r"^\s*(?:(?:quantas|quantos)\s+(?:as\s+)?a[cç][oõ]es|"
        r"(?:mostre|liste)\s+(?:as\s+)?a[cç][oõ]es)\s*[.!?]*\s*$",
        t, re.I,
    ):
        return {"action": "stats"}

    m = re.match(
        r"^\s*(?:procure|busque|encontre|pesquise)\s+"
        r"a[cç][oõ]es?\s+(?:para|sobre|de)\s+(.+?)\s*[.!?]*\s*$",
        t, re.I,
    )
    if m:
        return {"action": "search", "query": _clean_query(m.group(1))}

    m = re.match(
        r"^\s*(?:mostre|liste)\s+(?:as\s+)?a[cç][oõ]es?\s+"
        r"(?:(?:relacionadas?|relacionados?)\s+(?:a|ao|à|aos|às|com)|"
        r"(?:dispon[ií]veis?)\s+(?:para|sobre)|(?:para|sobre))\s+(.+?)\s*[.!?]*\s*$",
        t, re.I,
    )
    if m:
        return {"action": "search", "query": _clean_query(m.group(1))}

    m = re.match(
        r"^\s*quais\s+a[cç][oõ]es?\s+(?:existem\s+)?(?:para|sobre|de)\s+(.+?)\s*[.!?]*\s*$",
        t, re.I,
    )
    if m:
        return {"action": "search", "query": _clean_query(m.group(1))}

    m = re.match(r"^\s*use\s+(?:a\s+)?a[cç][aã]o\s+([\w.-]+)(?:\s+com\s+(\{.*\}))?\s*$", t, re.I | re.S)
    if m:
        params = {}
        if m.group(2):
            try:
                params = json.loads(m.group(2))
            except Exception:
                return {"action": "error", "error": "Parâmetros devem estar em JSON válido."}
        return {"action": "execute", "id": m.group(1), "params": params}

    if re.match(r"^\s*(?:abra|inicie)\s+(?:o\s+)?navegador\s+jarvis\s*$", t, re.I):
        return {"action": "execute", "id": "browser.start", "params": {}}

    m = re.match(r"^\s*(?:vá|va|navegue)\s+(?:para\s+)?(https?://\S+|\S+\.\S+)\s+(?:no\s+navegador\s+jarvis)?\s*$", t, re.I)
    if m:
        return {"action": "execute", "id": "browser.navigate", "params": {"url": m.group(1).rstrip(".")}}

    if re.match(r"^\s*(?:leia|resuma|extraia)\s+(?:a\s+)?p[aá]gina\s+(?:atual\s+)?(?:do\s+navegador\s+jarvis)?\s*$", t, re.I):
        return {"action": "execute", "id": "browser.text", "params": {"selector":"body","max_chars":12000}}

    m = re.match(r"^\s*(?:comece|inicie)\s+(?:a\s+)?observa[cç][aã]o(?:\s+(.+?))?\s*$", t, re.I)
    if m:
        return {"action": "execute", "id": "observe.start", "params": {"label": (m.group(1) or "demonstracao").strip()}}

    if re.match(r"^\s*(?:pare|encerre|finalize)\s+(?:a\s+)?observa[cç][aã]o\s*$", t, re.I):
        return {"action": "execute", "id": "observe.stop", "params": {}}

    if re.match(r"^\s*(?:status|estado)\s+(?:da\s+)?observa[cç][aã]o\s*$", t, re.I):
        return {"action": "execute", "id": "observe.status", "params": {}}

    return None
