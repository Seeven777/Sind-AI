import json
import ipaddress
import socket
import urllib.parse
import urllib.request
from pathlib import Path


def _is_public_https(url):
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != 'https' or not parsed.hostname:
            return False
        host = parsed.hostname.lower()
        if host in {'localhost', 'localhost.localdomain'}:
            return False
        try:
            infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            for info in infos:
                ip = ipaddress.ip_address(info[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                    return False
        except Exception:
            # DNS resolution may be unavailable before actual execution; hostname checks still apply.
            if host.startswith(('127.', '10.', '192.168.', '169.254.')):
                return False
        return True
    except Exception:
        return False


def _slug(value):
    out=[]
    for ch in str(value).lower():
        out.append(ch if ch.isalnum() else '.')
    s=''.join(out)
    while '..' in s: s=s.replace('..','.')
    return s.strip('.') or 'api'


def import_openapi_json(spec_url, prefix='imported', max_operations=60, user_agent='JarvisLocal/0.6'):
    if not _is_public_https(spec_url):
        return {'ok': False, 'error': 'Apenas especificações HTTPS públicas são permitidas.'}
    req = urllib.request.Request(spec_url, headers={'User-Agent': user_agent, 'Accept':'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read(4_000_000)
        spec = json.loads(raw.decode('utf-8', errors='replace'))
    except Exception as exc:
        return {'ok': False, 'error': f'Falha ao carregar OpenAPI JSON: {exc}'}

    servers = spec.get('servers') or []
    base = ''
    if servers and isinstance(servers[0], dict):
        base = servers[0].get('url') or ''
    if not base:
        # Swagger 2 fallback
        host = spec.get('host')
        base_path = spec.get('basePath','')
        schemes = spec.get('schemes') or ['https']
        if host:
            base = f"{schemes[0]}://{host}{base_path}"
    if not base or not _is_public_https(base if '{' not in base else base.split('{')[0]):
        return {'ok': False, 'error': 'A especificação não possui servidor HTTPS público compatível.'}

    title = ((spec.get('info') or {}).get('title') or prefix)
    capabilities=[]
    root_security = spec.get('security')
    for path, methods in (spec.get('paths') or {}).items():
        if len(capabilities) >= int(max_operations):
            break
        if not isinstance(methods, dict) or 'get' not in methods:
            continue
        op = methods.get('get') or {}
        # Skip operations requiring authentication. An explicit empty security list makes an operation public.
        effective_security = op.get('security', root_security)
        if effective_security:
            continue
        opid = op.get('operationId') or f"get_{path}"
        params={}
        all_params=[]
        all_params.extend(methods.get('parameters') or [])
        all_params.extend(op.get('parameters') or [])
        unsupported=False
        for prm in all_params:
            if '$ref' in prm:
                unsupported=True
                break
            loc=prm.get('in')
            if loc not in {'path','query'}:
                continue
            name=prm.get('name')
            if not name:
                continue
            params[name]={'in':loc,'required':bool(prm.get('required',False))}
            schema=prm.get('schema') or {}
            if 'default' in schema:
                params[name]['default']=schema['default']
        if unsupported:
            continue
        cid=f"openapi.{_slug(prefix)}.{_slug(opid)}"
        capabilities.append({
            'id':cid,
            'provider':title,
            'group':'discovered',
            'description':op.get('summary') or op.get('description') or f'GET {path}',
            'url':base.rstrip('/') + '/' + path.lstrip('/'),
            'method':'GET','auth':'none','risk':'read_only','response':'json',
            'params':params,'fixed_query':{},'keywords':['openapi','discovered',title],
            'cache_ttl':300,'min_interval':0.5,'discovered_from':spec_url,
        })
    return {'ok': True, 'title': title, 'capabilities': capabilities, 'count': len(capabilities)}


def save_imported(path, new_items):
    path=Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    current=[]
    if path.exists():
        try: current=json.loads(path.read_text(encoding='utf-8'))
        except Exception: current=[]
    by_id={x['id']:x for x in current if isinstance(x,dict) and x.get('id')}
    for item in new_items:
        by_id[item['id']]=item
    merged=sorted(by_id.values(), key=lambda x:x['id'])
    path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding='utf-8')
    return len(merged)
