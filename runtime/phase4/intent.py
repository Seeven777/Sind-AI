"""Conservative Portuguese intent routing for Phase 4."""
import re
import unicodedata
from dataclasses import dataclass


def fold(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(text or '').casefold())
        if unicodedata.category(c) != 'Mn'
    )


def identity(text):
    return unicodedata.normalize('NFKC', str(text or '')).strip().casefold()


@dataclass(frozen=True)
class Intent:
    executable: bool = False
    desktop: bool = False
    whatsapp: bool = False
    contact: str = ''
    message: str = ''


_ACTION_VERBS = (
    'abra', 'abrir', 'abre',
    'envie', 'enviar', 'envia', 'mande', 'mandar', 'manda',
    'digite', 'digitar', 'insira', 'inserir',
    'escreva', 'escrever', 'escreve', 'preencha', 'preencher',
    'clique', 'clicar', 'pressione',
    'execute', 'executar', 'gere', 'gerar', 'faca',
    'agende', 'automatize', 'salve', 'salvar', 'crie', 'criar',
    'mova', 'mover', 'copie', 'copiar', 'renomeie', 'apague', 'exclua',
    'publique', 'publicar', 'feche', 'fechar', 'selecione', 'selecionar',
    'aperte', 'acione', 'focalize',
)
_ACTION_ALT = '|'.join(map(re.escape, _ACTION_VERBS))
_SEND_ALT = r'envie|enviar|envia|mande|mandar|manda'


def _without_quoted_payloads(text):
    return re.sub(r'"[^"\n]*"|“[^”\n]*”|\'[^\'\n]*\'', '', text)


def _remove_negated_actions(command):
    out = re.sub(r'\bnao\s+(?:' + _ACTION_ALT + r')\b', ' ', command)
    out = re.sub(
        r'\bsem\s+(?:enviar|mandar|executar|abrir|clicar|pressionar|publicar|salvar|excluir|apagar)\b',
        ' ', out,
    )
    return re.sub(r'\s+', ' ', out).strip()


def _has_positive_action(command):
    return bool(re.search(r'\b(?:' + _ACTION_ALT + r')\b', command))


def _looks_informational(text):
    return bool(re.match(
        r'^(?:como\b|o que\b|qual\b|quais\b|por que\b|explique\b|me explique\b|'
        r'ensine\b|me ensine\b|se eu\b|suponha\b|simule\b|'
        r'(?:voce |vc )?(?:pode|consegue|sabe) (?:me )?(?:explicar|ensinar|dizer)\b|'
        r'(?:quero|gostaria de) (?:saber|entender|aprender)\b|'
        r'escreva (?:um |uma )?(?:texto|rascunho|mensagem)\b|'
        r'crie (?:um |uma )?(?:texto|rascunho|mensagem)\b)',
        text,
    ))


def _extract_multiline_whatsapp(raw):
    contact = ''
    message = ''
    for line in raw.splitlines():
        clean = line.strip()
        if not clean:
            continue
        m = re.match(
            r'^(?:selecione|selecionar|abra|abrir)\s+(?:a\s+)?(?:conversa|contato)\s+(.+?)\s*$',
            clean, flags=re.I,
        )
        if m:
            contact = m.group(1).strip().rstrip('.,;')
        m = re.match(
            r'^(?:escreva|digite|insira)\s+["“]([^"”]+)["”](?:\s+.*)?$',
            clean, flags=re.I,
        )
        if m:
            message = m.group(1)
    return contact, message


def _only_send_then_cancelled(t, positive_command):
    if not re.search(r'\b(?:mas|porem)\s+nao\s+(?:envie|enviar|mande|mandar)\b', t):
        return False
    without_send = re.sub(r'\b(?:' + _SEND_ALT + r')\b', ' ', positive_command)
    return not _has_positive_action(without_send)


def _quoted_send(raw):
    quoted = list(re.finditer(r'["“]([^"”]+)["”]', raw, flags=re.S))
    if len(quoted) != 1:
        return '', ''
    q = quoted[0]
    message = q.group(1)
    before = raw[:q.start()]
    after = raw[q.end():]

    if re.search(r'\b(?:' + _SEND_ALT + r')\b\s*$', fold(before), flags=re.I):
        recipient = re.match(
            r'\s*(?:para|pro|pra|ao|a)\s+(.+?)\s+(?:no|pelo|via|usando(?:\s+o)?)\s+whats\s*app(?:\s+desktop)?[.!?]?\s*$',
            after, flags=re.I | re.S,
        )
        if recipient:
            return recipient.group(1).strip(), message

    recipient = re.search(
        r'\b(?:envie|mande)\s+(?:para|pro|pra|ao|a)\s+(.+?)\s+(?:a\s+mensagem|a\s+msg|o\s+texto)\s*$',
        before, flags=re.I | re.S,
    )
    if recipient:
        return recipient.group(1).strip(), message
    return '', ''


def classify_intent(text):
    raw = str(text or '').strip()
    if not raw:
        return Intent()
    t = fold(raw)

    if _looks_informational(t):
        lines = [line.strip() for line in t.splitlines() if line.strip()]
        later_imperative = any(
            re.match(
                r'^(?:por favor[ ,]+)?(?:' + _ACTION_ALT + r')\b',
                _remove_negated_actions(_without_quoted_payloads(line)),
            )
            for line in lines[1:]
        )
        if not later_imperative:
            return Intent()

    positive_command = _remove_negated_actions(_without_quoted_payloads(t))
    if not _has_positive_action(positive_command):
        return Intent()

    wa_mentioned = bool(re.search(r'\bwhats\s*app\b', positive_command))
    desktop = wa_mentioned or bool(re.search(
        r'\b(?:janela|desktop|aplicativo|programa|botao|campo|tela|notepad|calculadora|'
        r'bloco de notas|digite|escreva|insira|preencha|clique|pressione|selecione|selecionar)\b',
        positive_command,
    ))

    if not wa_mentioned:
        return Intent(True, desktop)

    positive_send = bool(re.search(r'\b(?:' + _SEND_ALT + r')\b', positive_command))
    if _only_send_then_cancelled(t, positive_command):
        without_send = re.sub(r'\b(?:' + _SEND_ALT + r')\b', ' ', positive_command)
        if not _has_positive_action(without_send):
            return Intent()
        positive_send = False

    if not positive_send:
        return Intent(True, True, False)

    contact = ''
    message = ''
    colon = re.search(
        r'\b(?:para|pro|pra|ao|à)\s+([^:\n]+):[ \t]*(.+)$',
        raw, flags=re.I | re.S,
    )
    channel = r'\b(?:no|pelo|via|usando o|usando|do)\s+whats\s*app(?:\s+desktop)?\b(?:[.!?]\s*$)?'
    if colon:
        contact = re.sub(channel, '', colon.group(1), flags=re.I).strip()
        message = colon.group(2).strip()
    else:
        contact, message = _quoted_send(raw)

    step_contact, step_message = _extract_multiline_whatsapp(raw)
    if step_contact:
        contact = step_contact
    if step_message:
        message = step_message

    contact = re.sub(r'^(?:o|a|contato)\s+', '', contact, flags=re.I).strip()
    contact = re.sub(channel, '', contact, flags=re.I).strip().rstrip('.,;')
    message = str(message or '').strip()

    ambiguous_recipient = bool(
        re.search(r'\s+(?:e|ou)\s+', contact, flags=re.I)
        or ',' in contact
        or ';' in contact
    )
    if not contact or not message or '\n' in contact or ambiguous_recipient:
        contact = message = ''

    return Intent(True, True, True, contact, message)
