import io
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from capabilities.public_web import _safe_public_https


DATE_PATTERNS = [
    re.compile(r'\b([0-3]?\d/[01]?\d/20\d{2})\b'),
    re.compile(r'\b(20\d{2}-[01]\d-[0-3]\d)\b'),
    re.compile(r'\b([0-3]?\d\s+de\s+[A-Za-zÀ-ÿ]+\s+de\s+20\d{2})\b', re.I),
]


class SourceExtractor:
    def __init__(self, user_agent='JarvisSindPet/0.7.3'):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent,
            'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.6',
        })

    def _clean_text(self, value):
        value = re.sub(r'[ \t]+', ' ', str(value or ''))
        value = re.sub(r'\n\s*\n+', '\n\n', value)
        return value.strip()

    def _html_extract(self, html, final_url):
        soup = BeautifulSoup(html, 'html.parser')
        for tag in soup(['script','style','noscript','svg','canvas','form','nav','footer','aside']):
            tag.decompose()

        title = ''
        if soup.title:
            title = self._clean_text(soup.title.get_text(' ', strip=True))
        og_title = soup.find('meta', attrs={'property':'og:title'})
        if og_title and og_title.get('content'):
            title = self._clean_text(og_title.get('content')) or title

        description = ''
        md = soup.find('meta', attrs={'name': re.compile('^description$', re.I)})
        if md and md.get('content'):
            description = self._clean_text(md.get('content'))

        canonical = ''
        can = soup.find('link', rel=lambda v: v and 'canonical' in (v if isinstance(v, list) else [v]))
        if can and can.get('href'):
            canonical = can.get('href').strip()

        published = ''
        date_meta_keys = [
            ('property','article:published_time'), ('name','date'), ('name','publish-date'),
            ('name','pubdate'), ('itemprop','datePublished')
        ]
        for attr, key in date_meta_keys:
            n = soup.find('meta', attrs={attr:key})
            if n and n.get('content'):
                published = self._clean_text(n.get('content'))
                break

        root = soup.find('article') or soup.find('main') or soup.find(attrs={'role':'main'}) or soup.body or soup
        headings = []
        for h in root.find_all(re.compile('^h[1-6]$'))[:80]:
            txt = self._clean_text(h.get_text(' ', strip=True))
            if txt:
                headings.append({'level': h.name, 'text': txt})

        paragraphs = []
        for node in root.find_all(['p','li']):
            txt = self._clean_text(node.get_text(' ', strip=True))
            if len(txt) >= 35:
                paragraphs.append(txt)
        # Preserve useful page text when paragraph markup is poor.
        if len(' '.join(paragraphs)) < 500:
            raw = self._clean_text(root.get_text('\n', strip=True))
            paragraphs = [x.strip() for x in raw.split('\n') if len(x.strip()) >= 35]

        text = '\n\n'.join(paragraphs)
        if not published:
            sample = ' '.join(paragraphs[:8])
            for pattern in DATE_PATTERNS:
                m = pattern.search(sample)
                if m:
                    published = m.group(1)
                    break

        return {
            'title': title,
            'description': description,
            'canonical': canonical,
            'published': published,
            'headings': headings,
            'paragraphs': paragraphs[:300],
            'text': text,
            'content_kind': 'html',
            'url': final_url,
        }

    def _pdf_extract(self, raw, final_url):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        texts = []
        for page in reader.pages[:120]:
            try:
                texts.append(page.extract_text() or '')
            except Exception:
                texts.append('')
        text = self._clean_text('\n\n'.join(texts))
        meta = reader.metadata or {}
        return {
            'title': str(meta.get('/Title') or '').strip(),
            'description': '',
            'canonical': final_url,
            'published': str(meta.get('/CreationDate') or '').strip(),
            'headings': [],
            'paragraphs': [x for x in re.split(r'\n\s*\n', text) if x.strip()][:300],
            'text': text,
            'content_kind': 'pdf',
            'pages': len(reader.pages),
            'url': final_url,
        }

    def fetch(self, url, max_bytes=4_000_000):
        if not _safe_public_https(url):
            return {'ok': False, 'error': 'Somente URLs HTTPS públicas são permitidas.', 'url': str(url)}
        try:
            r = self.session.get(str(url), timeout=(6, 18), allow_redirects=True, stream=True)
            r.raise_for_status()
            final_url = r.url
            if not _safe_public_https(final_url):
                return {'ok': False, 'error': 'Destino final não público bloqueado.', 'url': final_url}
            raw = b''
            for chunk in r.iter_content(65536):
                raw += chunk
                if len(raw) > int(max_bytes):
                    break
            ctype = (r.headers.get('content-type') or '').lower()
            if 'pdf' in ctype or final_url.lower().split('?',1)[0].endswith('.pdf'):
                data = self._pdf_extract(raw, final_url)
            else:
                enc = r.encoding or 'utf-8'
                html = raw.decode(enc, errors='replace')
                data = self._html_extract(html, final_url)
            data.update({
                'ok': True,
                'status': r.status_code,
                'content_type': ctype,
                'bytes': len(raw),
            })
            return data
        except Exception as exc:
            return {'ok': False, 'error': str(exc), 'url': str(url)}

    def query_terms(self, query):
        stop = {'sobre','para','pela','pelo','com','sem','uma','um','que','das','dos','de','da','do','na','no','e','ou','em'}
        return [w for w in re.findall(r'[A-Za-zÀ-ÿ0-9-]+', str(query).lower()) if len(w) >= 2 and w not in stop]

    def relevant_sentences(self, text, query, limit=7):
        terms = self.query_terms(query)
        sentences = [self._clean_text(x) for x in re.split(r'(?<=[.!?])\s+|\n+', str(text))]
        ranked = []
        for i, sentence in enumerate(sentences):
            if len(sentence) < 45 or len(sentence) > 700:
                continue
            low = sentence.lower()
            hits = sum(1 for t in terms if t in low)
            exact = 4 if str(query).lower() in low else 0
            numeric = 1 if re.search(r'\b\d+(?:[.,]\d+)?%?\b', sentence) else 0
            score = hits * 3 + exact + numeric
            if score:
                ranked.append((score, -i, sentence))
        ranked.sort(reverse=True)
        selected = []
        seen = set()
        for _, _, sentence in ranked:
            key = re.sub(r'\W+',' ',sentence.lower())[:180]
            if key in seen:
                continue
            seen.add(key)
            selected.append(sentence)
            if len(selected) >= int(limit):
                break
        if not selected:
            selected = [s for s in sentences if 60 <= len(s) <= 500][:int(limit)]
        return selected
