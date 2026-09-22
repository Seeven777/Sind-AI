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

    m = re.match(r'^\s*digite\s+["“]?(.+?)["”]?\s*$', t, re.I)
    if m:
        return {"action": "type_text", "text": _clean(m.group(1))}

    m = re.match(
        r"^\s*pressione\s+(enter|tab|escape|esc|backspace|delete|"
        r"seta\s+para\s+cima|seta\s+para\s+baixo|seta\s+para\s+esquerda|"
        r"seta\s+para\s+direita)\s*$",
        t, re.I
    )
    if m:
        key = m.group(1).lower()
        mapping = {
            "seta para cima": "up", "seta para baixo": "down",
            "seta para esquerda": "left", "seta para direita": "right"
        }
        return {"action": "press_key", "key": mapping.get(key, key)}

    return None
