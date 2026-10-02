"""Pure UIA selectors, shared by desktop input and WhatsApp."""
from .intent import fold

SENSITIVE = ('senha', 'password', 'passcode', 'token', 'secret', 'segredo', 'api key', 'cvv', 'cartao')
SEARCH = ('pesquisar', 'pesquise', 'buscar', 'search')
COMPOSER = ('digite uma mensagem', 'escreva uma mensagem', 'type a message', 'message input', 'messageinput', 'compose', 'caixa de mensagem')


def _positive_area(item):
    bounds = item.get("bounds") or [0, 0, 0, 0]
    return max(0, bounds[2] - bounds[0]) * max(0, bounds[3] - bounds[1])


def choose_text_field(controls, name=None, purpose=None):
    ranked = []
    for item in controls:
        label = fold(item.get('name', '') + ' ' + item.get('automation_id', ''))
        geometrically_present = _positive_area(item) > 20
        if (item.get('control_type') not in ('Edit', 'Document') or
                (not item.get('visible') and not geometrically_present) or
                not item.get('enabled') or
                item.get('password') or item.get('read_only', True) or
                any(x in label for x in SENSITIVE)):
            continue
        is_search = any(x in label for x in SEARCH)
        is_composer = any(x in label for x in COMPOSER) or fold(item.get('name', '')).strip() in ('mensagem', 'message')
        if purpose == 'search' and not is_search:
            continue
        if purpose == 'message' and (not is_composer or is_search):
            continue
        if name:
            wanted = fold(name).strip()
            labels = (fold(item.get('name', '')), fold(item.get('automation_id', '')))
            score = 100 if wanted in labels else 60 if any(wanted in v for v in labels) else 0
            if not score:
                continue
        elif purpose:
            score = 100
            bounds = item.get('bounds') or [0, 0, 0, 0]
            top = bounds[1]
            if item.get('control_type') == 'Edit':
                score += 8
            if purpose == 'search':
                # Search lives near the top of the WhatsApp shell.
                score += max(0, 30 - max(0, top) // 120)
            elif purpose == 'message':
                # Composer lives near the bottom. Absolute Y is sufficient to
                # break duplicate WebView2 wrappers inside the same window.
                score += min(max(0, top) // 120, 30)
        else:
            score = 100 if item.get('focused') else 10
        ranked.append((score, item))
    if not ranked:
        raise RuntimeError('Nenhum campo de texto editável, visível e seguro foi identificado.')
    ranked.sort(key=lambda row: row[0], reverse=True)
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        # Fail closed. Two distinct UIA nodes may render at the same place in
        # WebView2; silently choosing one is unsafe for send/write operations.
        raise RuntimeError('Campo de texto ambíguo. Informe o nome ou automation_id exato.')
    return ranked[0][1]


def describe_control(ctrl, key=None):
    info = ctrl.element_info
    try:
        password = bool(info.element.CurrentIsPassword)
    except Exception:
        password = True
    try:
        read_only = bool(ctrl.iface_value.CurrentIsReadOnly)
    except Exception:
        read_only = True
    try:
        focused = bool(ctrl.has_keyboard_focus())
    except Exception:
        focused = False
    try:
        rect = ctrl.rectangle()
        bounds = [rect.left, rect.top, rect.right, rect.bottom]
    except Exception:
        bounds = [0, 0, 0, 0]
    return {'key': key, 'name': info.name or '', 'automation_id': info.automation_id or '',
            'control_type': info.control_type, 'visible': bool(ctrl.is_visible()),
            'enabled': bool(ctrl.is_enabled()), 'password': password,
            'read_only': read_only, 'focused': focused, 'bounds': bounds}
