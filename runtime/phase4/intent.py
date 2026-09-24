"""Conservative Portuguese intent routing. Parsing never invents message text."""
import re
import unicodedata
from dataclasses import dataclass


def fold(text):
    return ''.join(c for c in unicodedata.normalize('NFD', str(text or '').casefold())
                   if unicodedata.category(c) != 'Mn')


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


def classify_intent(text):
    raw = str(text or '').strip()
    t = fold(raw)
    # Explanations, hypotheticals, quotations and drafts are not authorization.
    if re.match(r'^(?:como\b|o que\b|qual\b|quais\b|por que\b|explique\b|me explique\b|'
                r'ensine\b|me ensine\b|se eu\b|suponha\b|simule\b|nao\b|'
                r'(?:voce |vc )?(?:pode|consegue|sabe) (?:me )?(?:explicar|ensinar|dizer)\b|'
                r'(?:quero|gostaria de) (?:saber|entender|aprender)\b|'
                r'escreva (?:um |uma )?(?:texto|rascunho|mensagem)\b|'
                r'crie (?:um |uma )?(?:texto|rascunho|mensagem)\b)', t):
        return Intent()
    # Ignore action words inside quoted payloads when deciding intent.
    command = re.sub(r'"[^"]*"|“[^”]*”|\'[^\']*\'', '', t).split(':', 1)[0]
    if re.search(r'\b(?:nao (?:envie|mande|execute|abra)|sem enviar|apenas (?:simule|explique|rascunho)|so (?:simule|explique))\b', command):
        return Intent()
    verbs = r'(?:abra|abrir|abre|envie|enviar|envia|mande|mandar|manda|digite|digitar|clique|clicar|pressione|execute|executar|gere|gerar|faca|agende|automatize|salve|salvar|crie|criar|mova|mover|copie|copiar|renomeie|apague|exclua|publique|publicar|feche|fechar|selecione|aperte|acione|focalize)'
    executable = bool(re.search(r'\b' + verbs + r'\b', command))
    wa = executable and bool(re.search(r'\bwhats\s*app\b', command))
    desktop = wa or (executable and bool(re.search(
        r'\b(?:janela|desktop|aplicativo|programa|botao|campo|tela|notepad|calculadora|bloco de notas|digite|clique|pressione|selecione)\b', command)))
    if not wa:
        return Intent(executable, desktop)
    # Supported unambiguous forms retain punctuation and case of the payload.
    # Envie no WhatsApp para Maria: texto
    # Envie "texto" para Maria no WhatsApp
    # Abra o WhatsApp e envie para Maria a mensagem "texto"
    if not re.search(r'\b(?:envie|enviar|envia|mande|mandar|manda)\b', command):
        return Intent(True, True, False)
    contact = message = ''
    # Extract payload before removing channel words: literal text may itself contain
    # "no WhatsApp", quotes, colons or action verbs. Never normalize that payload.
    colon = re.search(r'\b(?:para|pro|pra|ao|à)\s+([^:\n]+):[ \t]*(.+)$', raw, flags=re.I | re.S)
    channel = r'\b(?:no|pelo|via|usando o|usando|do)\s+whats\s*app(?:\s+desktop)?\b(?:[.!?]\s*$)?'
    if colon:
        contact = re.sub(channel, '', colon.group(1), flags=re.I).strip()
        message = colon.group(2)
    else:
        quoted = list(re.finditer(r'["“]([^"”]+)["”]', raw, flags=re.S))
        if len(quoted) == 1:
            quote = quoted[0]
            message = quote.group(1)
            outside = raw[:quote.start()] + raw[quote.end():]
            outside = re.sub(channel, '', outside, flags=re.I)
            outside = re.sub(r'^.*?\b(?:envie|enviar|envia|mande|mandar|manda)\b\s*', '', outside, count=1, flags=re.I)
            match = re.search(r'\b(?:para|pro|pra|ao|à)\s+(.+?)\s*$', outside, flags=re.I | re.S)
            if match:
                contact = re.sub(r'\s+(?:(?:a|uma)\s+)?mensagem\s*$', '', match.group(1), flags=re.I).strip()
    contact = re.sub(r'^(?:o|a|contato)\s+', '', contact, flags=re.I).strip()
    if not contact or not message.strip() or re.search(r'\b(?:e|ou)\b|[,;\n]', contact, re.I):
        contact = message = ''
    return Intent(True, True, True, contact, message)
