import re


def _clean(v):
    return str(v).strip().strip('"').strip("'").rstrip(" .!?;:")


def parse_access_command(text):
    t = str(text).strip()

    m = re.match(r"^\s*(?:selecione|use|focalize)\s+(?:a\s+)?janela\s+(.+?)\s*$", t, re.I)
    if m:
        return {"action": "select_window", "query": _clean(m.group(1))}

    if re.match(r"^\s*(?:qual|qual\s+é|qual\s+e)\s+(?:a\s+)?janela\s+selecionada\??\s*$", t, re.I):
        return {"action": "selected_window"}

    if re.match(r"^\s*(?:observe|inspecione|analise)\s+(?:a\s+)?janela\s+selecionada\s*$", t, re.I):
        return {"action": "inspect_window"}

    m = re.match(r"^\s*(?:clique|aperte|acione)\s+(?:em\s+)?(.+?)\s*$", t, re.I)
    if m:
        return {"action": "click_control", "name": _clean(m.group(1))}

    m = re.match(r'^\s*(?:digite|escreva|insira|preencha)\s+["“\']?(.+?)["”\']?\s*$', t, re.I)
    if m:
        return {"action": "type_text", "text": m.group(1).strip()}

    # Runtime V2 accepts common shortcuts while keeping the same public tool.
    m = re.match(
        r"^\s*(?:pressione|aperte|use\s+(?:o\s+)?atalho|atalho)\s+(.+?)\s*$",
        t,
        re.I,
    )
    if m:
        key = _clean(m.group(1)).lower()
        replacements = {
            "seta para cima": "up", "seta para baixo": "down",
            "seta para esquerda": "left", "seta para direita": "right",
            "página para baixo": "pagedown", "pagina para baixo": "pagedown",
            "página para cima": "pageup", "pagina para cima": "pageup",
        }
        key = replacements.get(key, key)
        return {"action": "press_key", "key": key}

    if re.match(r"^\s*(?:role|rolar|desça|desca)\s+(?:a\s+)?(?:tela\s+)?(?:para\s+)?baixo\s*$", t, re.I):
        return {"action": "press_key", "key": "pagedown"}
    if re.match(r"^\s*(?:role|rolar|suba)\s+(?:a\s+)?(?:tela\s+)?(?:para\s+)?cima\s*$", t, re.I):
        return {"action": "press_key", "key": "pageup"}

    return None
