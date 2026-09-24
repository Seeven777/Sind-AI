"""Conservative Portuguese intent routing for Phase 4.

Execution authorization comes from explicit imperative requests. Negation is local:
"digite X, mas não envie" still authorizes typing while blocking sending. A later
explicit "envie" is a new positive instruction and may authorize the send.
"""
import re
import unicodedata
from dataclasses import dataclass


def fold(text):
    return ''.join(
        c for c in unicodedata.normalize('NFD', str(text or '').casefold())
        if unicodedata.category(c) != 'Mn'
    )


def identity(text):
    """Recipient identity keeps accents; command normalization does not."""
    return unicodedata.normalize('NFKC', str(text or '')).strip().casefold()


@dataclass(frozen=True)
class Intent:
    executable: bool = False
    desktop: bool = False
    whatsapp: bool = False
    contact: str = ''
    message: str = ''


# Physical/operational verbs. "escreva" is deliberately not universal here:
# writing a document can be a content-generation request; desktop context and
# other imperative verbs still make sequences such as the WhatsApp benchmark
# executable.
_ACTION_VERBS = (
    'abra', 'abrir', 'abre',
    'envie', 'enviar', 'envia', 'mande', 'mandar', 'manda',
    'digite', 'digitar', 'insira', 'inserir',
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
    """Remove quoted payloads so action words inside a message do not authorize UI actions."""
    return re.sub(r'"[^"\n]*"|“[^”\n]*”|\'[^\'\n]*\'', '', text)


def _remove_negated_actions(command):
    """Remove only the negated action itself, never the whole request."""
    out = command
    # "não envie", "nao abra", etc.
    out = re.sub(r'\bnao\s+(?:' + _ACTION_ALT + r')\b', ' ', out)
    # "sem enviar", "sem abrir" are local prohibitions too.
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
    """Extract contact/message from an explicit step-by-step WhatsApp request.

    Supported example:
        abra o WhatsApp
        selecione a conversa Me (você)
        escreva "teste fase 4" no campo de mensagem, mas não envie
        envie a mensagem
    """
    contact = ''
    message = ''

    for line in raw.splitlines():
        clean = line.strip()
        if not clean:
            continue

        m = re.match(
            r'^(?:selecione|selecionar|abra|abrir)\s+(?:a\s+)?(?:conversa|contato)\s+(.+?)\s*$',
            clean,
            flags=re.I,
        )
        if m:
            candidate = m.group(1).strip().rstrip('.,;')
            if candidate:
                contact = candidate

        m = re.match(
            r'^(?:escreva|digite|insira)\s+["“]([^"”]+)["”](?:\s+.*)?$',
            clean,
            flags=re.I,
        )
        if m:
            message = m.group(1)

    return contact, message


def classify_intent(text):
    raw = str(text or '').strip()
    if not raw:
        return Intent()

    t = fold(raw)

    # Questions such as "Como enviar...?" contain an infinitive action word,
    # but do not authorize execution. A later independent imperative line does.
    if _looks_informational(t):
        lines = [line.strip() for line in t.splitlines() if line.strip()]
        later_imperative = any(
            re.match(r'^(?:por favor[ ,]+)?(?:' + _ACTION_ALT + r')\b',
                     _remove_negated_actions(_without_quoted_payloads(line)))
            for line in lines[1:]
        )
        if not later_imperative:
            return Intent()

    # Ignore action words contained in literal payloads. Keep newlines so we can
    # reason about sequential commands, but never let a local "não envie" cancel
    # unrelated positive actions before/after it.
    command_with_lines = _without_quoted_payloads(t)
    positive_command = _remove_negated_actions(command_with_lines)

    executable = _has_positive_action(positive_command)

    # Explicit explanation/simulation remains informational only when there is
    # no independent positive operational command anywhere in the request.
    if not executable and _looks_informational(t):
        return Intent()

    # "não abra..." / "não envie..." with no other positive action is not an
    # authorization. Likewise pure explanation/draft requests remain passive.
    if not executable:
        return Intent()

    wa_mentioned = bool(re.search(r'\bwhats\s*app\b', positive_command))
    desktop = wa_mentioned or bool(re.search(
        r'\b(?:janela|desktop|aplicativo|programa|botao|campo|tela|notepad|calculadora|'
        r'bloco de notas|digite|clique|pressione|selecione|selecionar)\b',
        positive_command,
    ))

    if not wa_mentioned:
        return Intent(True, desktop)

    # WhatsApp was explicitly requested. Only enter the deterministic SEND path
    # when there is a positive send verb after local negations are removed.
    positive_send = bool(re.search(r'\b(?:' + _SEND_ALT + r')\b', positive_command))
    if not positive_send:
        # e.g. "Abra o WhatsApp e digite X, mas não envie". This remains a real
        # desktop task but must not call whatsapp_send_message.
        return Intent(True, True, False)

    contact = ''
    message = ''

    # 1) Strong format: "Envie no WhatsApp para Maria: Olá!"
    colon = re.search(
        r'\b(?:para|pro|pra|ao|à)\s+([^:\n]+):[ \t]*(.+)$',
        raw,
        flags=re.I | re.S,
    )
    channel = r'\b(?:no|pelo|via|usando o|usando|do)\s+whats\s*app(?:\s+desktop)?\b(?:[.!?]\s*$)?'
    if colon:
        contact = re.sub(channel, '', colon.group(1), flags=re.I).strip()
        message = colon.group(2).strip()
    else:
        # 2) Compact quoted form: Envie "Olá" para Maria no WhatsApp.
        quoted = list(re.finditer(r'["“]([^"”]+)["”]', raw, flags=re.S))
        if len(quoted) == 1:
            quote = quoted[0]
            message = quote.group(1)
            outside = raw[:quote.start()] + raw[quote.end():]
            outside = re.sub(channel, '', outside, flags=re.I)
            outside_folded = fold(outside)
            # Use only positive send occurrences. A preceding "não envie" must
            # not be mistaken for the command that identifies the recipient.
            outside_folded = _remove_negated_actions(outside_folded)
            match = re.search(
                r'\b(?:' + _SEND_ALT + r')\b.*?\b(?:para|pro|pra|ao|a)\s+(.+?)\s*$',
                outside_folded,
                flags=re.I | re.S,
            )
            if match:
                # This normalized branch is useful only for simple forms. Keep
                # original capitalization where possible below via multiline parse.
                contact = match.group(1).strip()

    # 3) Explicit multi-step form used by the Phase 4 benchmark.
    step_contact, step_message = _extract_multiline_whatsapp(raw)
    if step_contact:
        contact = step_contact
    if step_message:
        message = step_message

    contact = re.sub(r'^(?:o|a|contato)\s+', '', contact, flags=re.I).strip()
    contact = re.sub(channel, '', contact, flags=re.I).strip().rstrip('.,;')
    message = str(message or '').strip()

    # Do not invent ambiguous recipients. Parentheses are valid ("Me (você)").
    if (not contact or not message or '\n' in contact or ',' in contact or ';' in contact):
        contact = message = ''

    return Intent(True, True, True, contact, message)
