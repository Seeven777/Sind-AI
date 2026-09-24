"""Pure UIA selectors, shared by desktop input and WhatsApp."""
from .intent import fold

SENSITIVE = ('senha', 'password', 'passcode', 'token', 'secret', 'segredo', 'api key', 'cvv', 'cartao')
SEARCH = ('pesquisar', 'pesquise', 'buscar', 'search')
COMPOSER = ('digite uma mensagem', 'escreva uma mensagem', 'type a message', 'message input', 'messageinput', 'compose', 'caixa de mensagem')


def choose_text_field(controls, name=None, purpose=None):
    ranked = []
    for item in controls:
        label = fold(item.get('name', '') + ' ' + item.get('automation_id', ''))
        if (item.get('control_type') not in ('Edit', 'Document') or
                not item.get('visible') or not item.get('enabled') or
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
        else:
            score = 100 if item.get('focused') else 10
        ranked.append((score, item))
    if not ranked:
        raise RuntimeError('Nenhum campo de texto editável, visível e seguro foi identificado.')
    ranked.sort(key=lambda row: row[0], reverse=True)
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
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
