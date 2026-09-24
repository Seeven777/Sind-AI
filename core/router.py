import re


def fast_path(text, desktop):
    t = text.strip()
    l = t.lower()

    m = re.search(
        r"(?:crie|criar|faça|faca)\s+(?:uma\s+)?pasta(?:\s+chamada|\s+com\s+o\s+nome\s+de)?\s+[\"']?([^\"']+?)[\"']?\s+(?:na|no)\s+(?:minha\s+)?(?:área|area)\s+de\s+trabalho",
        t, flags=re.I
    )
    if m:
        return "create_folder", {"path": str(desktop / m.group(1).strip().rstrip("."))}

    # Fast paths are deliberately restricted to atomic open-only requests. A
    # compound command must continue into the agent/Phase-4 runtime instead of
    # being truncated after the first "abra" clause.
    if re.fullmatch(r"\s*(?:por favor[, ]+)?(?:abra|abrir|abre)\s+(?:o\s+)?bloco de notas\s*[.!]?\s*", l):
        return "open_app", {"app": "notepad"}
    if re.fullmatch(r"\s*(?:por favor[, ]+)?(?:abra|abrir|abre)\s+(?:a\s+)?calculadora\s*[.!]?\s*", l):
        return "open_app", {"app": "calc"}
    if re.fullmatch(
        r"\s*(?:por favor[, ]+)?(?:abra|abrir|abre|inicie|iniciar)\s+(?:o\s+)?(?:whatsapp|whats app)(?:\s+desktop)?\s*[.!]?\s*",
        l,
    ):
        return "open_app", {"app": "whatsapp"}
    if re.fullmatch(r"\s*(?:por favor[, ]+)?(?:abra|abrir|abre)\s+(?:a\s+)?(?:área|area) de trabalho\s*[.!]?\s*", l):
        return "open_folder", {"path": str(desktop)}

    if any(x in l for x in ["tire um screenshot", "tire uma captura", "capture a tela"]):
        return "take_screenshot", {}
    if "clipboard" in l and any(x in l for x in ["o que", "qual texto", "leia"]):
        return "get_clipboard", {}

    m = re.search(r"\b(?:abra|abrir)\b.*?\b((?:https?://)?(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:/\S*)?)", l, re.I)
    if m:
        return "open_url", {"url": m.group(1)}

    return None
