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

    if "abra" in l and "bloco de notas" in l:
        return "open_app", {"app": "notepad"}
    if "abra" in l and "calculadora" in l:
        return "open_app", {"app": "calc"}
    if any(x in l for x in ["whatsapp", "whats app"]) and any(x in l for x in ["abra", "abrir", "abre", "inicie", "iniciar"]):
        return "open_app", {"app": "whatsapp"}
    if "abra" in l and ("área de trabalho" in l or "area de trabalho" in l):
        return "open_folder", {"path": str(desktop)}
    if any(x in l for x in ["tire um screenshot", "tire uma captura", "capture a tela"]):
        return "take_screenshot", {}
    if "clipboard" in l and any(x in l for x in ["o que", "qual texto", "leia"]):
        return "get_clipboard", {}

    m = re.search(r"\b(?:abra|abrir)\b.*?\b((?:https?://)?(?:www\.)?[a-z0-9.-]+\.[a-z]{2,}(?:/\S*)?)", l, re.I)
    if m:
        return "open_url", {"url": m.group(1)}

    return None
