import html
import ipaddress
import json
import re
import socket
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from html.parser import HTMLParser


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.skip=0
    def handle_starttag(self, tag, attrs):
        if tag.lower() in {'script','style','noscript','svg'}:
            self.skip += 1
        if tag.lower() in {'p','div','br','li','h1','h2','h3','h4','article','section'} and not self.skip:
            self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag.lower() in {'script','style','noscript','svg'} and self.skip:
            self.skip -= 1
        if tag.lower() in {'p','div','li','article','section'} and not self.skip:
            self.parts.append('\n')
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)
    def text(self):
        t=html.unescape(' '.join(self.parts))
        t=re.sub(r'[ \t]+',' ',t)
        t=re.sub(r'\n\s*\n+','\n\n',t)
        return t.strip()


def _safe_public_https(url):
    try:
        parsed=urllib.parse.urlparse(str(url))
        if parsed.scheme != 'https' or not parsed.hostname:
            return False
        host=parsed.hostname.lower()
        if host in {'localhost','localhost.localdomain'}:
            return False
        try:
            for info in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM):
                ip=ipaddress.ip_address(info[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False
        except Exception:
            if host.startswith(('127.','10.','192.168.','169.254.')):
                return False
        return True
    except Exception:
        return False


def fetch_public_url(url, max_chars=18000):
    if not _safe_public_https(url):
        return {'ok':False,'error':'Somente URLs HTTPS públicas são permitidas.'}
    try:
        req=urllib.request.Request(str(url),headers={'User-Agent':'JarvisSindPet/0.6','Accept':'text/html,application/json,text/plain,application/xml;q=0.8,*/*;q=0.5'})
        with urllib.request.urlopen(req,timeout=20) as resp:
            raw=resp.read(2_000_000)
            ctype=(resp.headers.get('Content-Type') or '').lower()
            charset=resp.headers.get_content_charset() or 'utf-8'
            text=raw.decode(charset,errors='replace')
            final_url=resp.geturl()
        if not _safe_public_https(final_url):
            return {'ok':False,'error':'Redirecionamento para destino não público foi bloqueado.','url':final_url}
        if 'json' in ctype:
            try:
                payload=json.loads(text)
                rendered=json.dumps(payload,ensure_ascii=False,indent=2)
            except Exception:
                rendered=text
        elif 'html' in ctype:
            parser=_TextExtractor(); parser.feed(text); rendered=parser.text()
        else:
            rendered=text
        return {'ok':True,'url':final_url,'content_type':ctype,'text':rendered[:int(max_chars)]}
    except Exception as exc:
        return {'ok':False,'error':str(exc),'url':str(url)}


def read_rss(url, limit=20):
    if not _safe_public_https(url):
        return {'ok':False,'error':'Somente feeds HTTPS públicos são permitidos.'}
    try:
        req=urllib.request.Request(str(url),headers={'User-Agent':'JarvisSindPet/0.6','Accept':'application/rss+xml,application/atom+xml,application/xml,text/xml'})
        with urllib.request.urlopen(req,timeout=20) as resp:
            raw=resp.read(2_000_000)
        root=ET.fromstring(raw)
        entries=[]
        # RSS
        for item in root.findall('.//item')[:int(limit)]:
            entries.append({
                'title': (item.findtext('title') or '').strip(),
                'link': (item.findtext('link') or '').strip(),
                'published': (item.findtext('pubDate') or '').strip(),
                'description': re.sub('<[^>]+>',' ',item.findtext('description') or '').strip()[:1000],
            })
        # Atom fallback
        if not entries:
            ns={'a':'http://www.w3.org/2005/Atom'}
            for item in root.findall('.//a:entry',ns)[:int(limit)]:
                link=''
                ln=item.find('a:link',ns)
                if ln is not None: link=ln.attrib.get('href','')
                entries.append({
                    'title': (item.findtext('a:title',default='',namespaces=ns) or '').strip(),
                    'link': link,
                    'published': (item.findtext('a:updated',default='',namespaces=ns) or item.findtext('a:published',default='',namespaces=ns) or '').strip(),
                    'description': re.sub('<[^>]+>',' ',item.findtext('a:summary',default='',namespaces=ns) or '').strip()[:1000],
                })
        return {'ok':True,'url':str(url),'items':entries,'count':len(entries)}
    except Exception as exc:
        return {'ok':False,'error':str(exc),'url':str(url)}
