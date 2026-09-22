import base64
import re
import urllib.parse
from dataclasses import dataclass


TRACKING_KEYS = {
    'utm_source','utm_medium','utm_campaign','utm_term','utm_content','utm_id',
    'gclid','fbclid','msclkid','mc_cid','mc_eid','ref','ref_src','source'
}

OFFICIAL_PATTERNS = [
    (re.compile(r'(^|\.)gov\.br$', re.I), 100, 'governo'),
    (re.compile(r'(^|\.)planalto\.gov\.br$', re.I), 112, 'legislacao'),
    (re.compile(r'(^|\.)in\.gov\.br$', re.I), 112, 'diario_oficial'),
    (re.compile(r'(^|\.)tst\.jus\.br$', re.I), 108, 'judiciario'),
    (re.compile(r'(^|\.)trt\d*\.jus\.br$', re.I), 105, 'judiciario'),
    (re.compile(r'(^|\.)stf\.jus\.br$', re.I), 108, 'judiciario'),
    (re.compile(r'(^|\.)stj\.jus\.br$', re.I), 108, 'judiciario'),
    (re.compile(r'(^|\.)mpt\.mp\.br$', re.I), 106, 'ministerio_publico'),
    (re.compile(r'(^|\.)mpf\.mp\.br$', re.I), 104, 'ministerio_publico'),
    (re.compile(r'(^|\.)fundacentro\.gov\.br$', re.I), 108, 'tecnico_oficial'),
    (re.compile(r'(^|\.)ibge\.gov\.br$', re.I), 106, 'estatistica_oficial'),
    (re.compile(r'(^|\.)bcb\.gov\.br$', re.I), 106, 'banco_central'),
    (re.compile(r'(^|\.)camara\.leg\.br$', re.I), 104, 'legislativo'),
    (re.compile(r'(^|\.)senado\.leg\.br$', re.I), 104, 'legislativo'),
]

ACADEMIC_PATTERNS = [
    re.compile(r'(^|\.)scielo\.br$', re.I),
    re.compile(r'(^|\.)pubmed\.ncbi\.nlm\.nih\.gov$', re.I),
    re.compile(r'(^|\.)doi\.org$', re.I),
    re.compile(r'(^|\.)arxiv\.org$', re.I),
    re.compile(r'(^|\.)crossref\.org$', re.I),
    re.compile(r'(^|\.)openalex\.org$', re.I),
]

NEWS_DOMAINS = {
    'g1.globo.com','www1.folha.uol.com.br','folha.uol.com.br','estadao.com.br',
    'www.estadao.com.br','cnnbrasil.com.br','www.cnnbrasil.com.br','agenciabrasil.ebc.com.br',
    'valor.globo.com','uol.com.br','noticias.uol.com.br'
}


def _pad_b64(value):
    return value + ('=' * ((4 - len(value) % 4) % 4))


def decode_bing_redirect(url):
    """Decode common Bing /ck/a redirect URLs into the real target URL."""
    try:
        p = urllib.parse.urlsplit(str(url))
        host = (p.hostname or '').lower()
        if 'bing.com' not in host:
            return str(url)
        q = dict(urllib.parse.parse_qsl(p.query, keep_blank_values=True))
        raw = q.get('u') or q.get('url') or q.get('r')
        if not raw:
            return str(url)
        raw = urllib.parse.unquote(raw)
        # Bing often prefixes base64url targets with "a1".
        candidates = [raw]
        if raw.startswith('a1'):
            candidates.insert(0, raw[2:])
        for candidate in candidates:
            try:
                decoded = base64.urlsafe_b64decode(_pad_b64(candidate)).decode('utf-8', errors='strict')
                if decoded.startswith(('https://','http://')):
                    return decoded
            except Exception:
                pass
        if raw.startswith(('https://','http://')):
            return raw
    except Exception:
        pass
    return str(url)


def decode_google_redirect(url):
    try:
        p = urllib.parse.urlsplit(str(url))
        host = (p.hostname or '').lower()
        if 'google.' not in host and host != 'google.com':
            return str(url)
        if p.path not in {'/url','/imgres'}:
            return str(url)
        q = dict(urllib.parse.parse_qsl(p.query, keep_blank_values=True))
        target = q.get('q') or q.get('url') or q.get('imgurl')
        if target and target.startswith(('https://','http://')):
            return target
    except Exception:
        pass
    return str(url)


def decode_ddg_redirect(url):
    try:
        p = urllib.parse.urlsplit(str(url))
        host = (p.hostname or '').lower()
        if 'duckduckgo.com' not in host:
            return str(url)
        q = dict(urllib.parse.parse_qsl(p.query, keep_blank_values=True))
        target = q.get('uddg')
        if target:
            target = urllib.parse.unquote(target)
            if target.startswith(('https://','http://')):
                return target
    except Exception:
        pass
    return str(url)


def strip_tracking(url):
    try:
        p = urllib.parse.urlsplit(str(url))
        clean_query = []
        for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True):
            if k.lower() in TRACKING_KEYS or k.lower().startswith('utm_'):
                continue
            clean_query.append((k, v))
        path = re.sub(r'/{2,}', '/', p.path or '/')
        return urllib.parse.urlunsplit((p.scheme, p.netloc, path, urllib.parse.urlencode(clean_query, doseq=True), ''))
    except Exception:
        return str(url)


def normalize_url(url):
    value = str(url or '').strip()
    if not value:
        return ''
    value = decode_bing_redirect(value)
    value = decode_google_redirect(value)
    value = decode_ddg_redirect(value)
    if value.startswith('http://'):
        # Prefer HTTPS for public research whenever possible.
        value = 'https://' + value[len('http://'):]
    return strip_tracking(value)


def domain_of(url):
    try:
        return (urllib.parse.urlsplit(str(url)).hostname or '').lower().removeprefix('www.')
    except Exception:
        return ''


def classify_domain(domain):
    d = str(domain or '').lower().removeprefix('www.')
    for pattern, score, label in OFFICIAL_PATTERNS:
        if pattern.search(d):
            return label, score
    if any(p.search(d) for p in ACADEMIC_PATTERNS):
        return 'academico', 88
    if d in NEWS_DOMAINS or any(d.endswith('.' + x) for x in NEWS_DOMAINS):
        return 'imprensa', 68
    if d.endswith('.edu.br') or d.endswith('.edu'):
        return 'educacional', 82
    if d.endswith('.org.br') or d.endswith('.org'):
        return 'organizacao', 62
    if d:
        return 'web', 50
    return 'desconhecido', 0


def authority_score(url, query=''):
    domain = domain_of(url)
    label, base = classify_domain(domain)
    q = str(query or '').lower()
    if 'nr-' in q or re.search(r'\bnr\s*\d+', q):
        if 'trabalho-e-emprego' in str(url).lower():
            base += 15
        if domain.endswith('fundacentro.gov.br'):
            base += 10
    return min(130, base), label


def source_identity(url, query=''):
    normalized = normalize_url(url)
    domain = domain_of(normalized)
    score, label = authority_score(normalized, query=query)
    return {
        'url': normalized,
        'domain': domain,
        'authority_score': score,
        'source_type': label,
        'official': score >= 100,
    }
