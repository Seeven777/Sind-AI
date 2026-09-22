import json
import re
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import requests

from knowledge.base import KnowledgeBase
from training.engine import TrainingEngine
from team_assistant.engine import TeamAssistantEngine

SESSIONS = {}
SESSION_LOCK = threading.Lock()


class TeamPortalApp:
    def __init__(self, team, knowledge, training, ollama_url, model):
        self.team = team
        self.knowledge = knowledge
        self.training = training
        self.ollama_url = str(ollama_url).rstrip('/')
        self.model = model

    def settings(self):
        rows = self.team.setting_get().get('items', [])
        return {x['key']: x['value'] for x in rows}

    def create_session(self, user):
        token = secrets.token_urlsafe(32)
        with SESSION_LOCK:
            SESSIONS[token] = {'user': user, 'created': time.time(), 'last': time.time()}
        return token

    def session(self, token):
        if not token:
            return None
        with SESSION_LOCK:
            s = SESSIONS.get(token)
            if not s:
                return None
            if time.time() - s['last'] > 12 * 3600:
                SESSIONS.pop(token, None)
                return None
            s['last'] = time.time()
            return s['user']

    def logout(self, token):
        with SESSION_LOCK:
            SESSIONS.pop(token, None)

    def allowed_collections(self, user):
        all_cols = [x['collection'] for x in self.knowledge.list_collections().get('items', [])]
        role_id = user.get('role_id')
        if (user.get('role_name') or '').lower() in {'admin', 'administrador'}:
            return all_cols
        if not role_id:
            return []
        grants = self.team.collection_grant_list(role_id).get('items', [])
        return [x['collection'] for x in grants if x.get('access_level') in {'read', 'write', 'admin'}]

    def allowed_tracks(self, user):
        if self.training is None:
            return []
        all_tracks = self.training.execute('track_list', status='active', limit=500).get('items', [])
        role_id = user.get('role_id')
        if (user.get('role_name') or '').lower() in {'admin', 'administrador'}:
            return all_tracks
        if not role_id:
            return []
        grants = {int(x['track_id']) for x in self.team.track_grant_list(role_id).get('items', [])}
        return [x for x in all_tracks if int(x['id']) in grants]

    def evidence(self, user, question, max_sources=6):
        collections = self.allowed_collections(user)
        items = []
        seen = set()
        per = max(1, min(4, int(max_sources)))

        # FTS5 normally treats terms as AND. For natural questions this can be
        # too strict, so we progressively relax the query without inventing facts.
        stop = {
            'a','o','as','os','um','uma','de','da','do','das','dos','e','é','em',
            'no','na','nos','nas','para','por','com','sem','que','como','qual',
            'quais','onde','quando','eu','me','meu','minha','isso','isto','se',
            'ao','aos','à','às','sobre'
        }
        tokens = [
            x.lower()
            for x in re.findall(r"[A-Za-zÀ-ÿ0-9_-]{3,}", str(question))
            if x.lower() not in stop
        ]
        variants = [str(question).strip()]
        if tokens:
            variants.append(" ".join(tokens[:5]))
            variants.extend(tokens[:5])

        for collection in collections:
            for variant in variants:
                if len(items) >= int(max_sources):
                    break
                result = self.knowledge.search(collection, variant, limit=per)
                for x in result.get('items', []):
                    key = (collection, x.get('document_id'), x.get('chunk_id'))
                    if key in seen:
                        continue
                    seen.add(key)
                    items.append({
                        'collection': collection,
                        'document_id': x.get('document_id'),
                        'chunk_id': x.get('chunk_id'),
                        'title': x.get('title'),
                        'source': x.get('source'),
                        'text': x.get('text', '')[:1200],
                        'score': x.get('score'),
                        'matched_query': variant,
                    })
                    if len(items) >= int(max_sources):
                        break
        return items[:int(max_sources)]

    def answer(self, user, question):
        settings = self.settings()
        max_sources = int(settings.get('max_sources', '6'))
        evidence = self.evidence(user, question, max_sources=max_sources)
        if not evidence:
            self.team.gap_add(question, category='team_portal', source=user.get('username', 'team'))
            self.team.ask_log_add(user.get('id'), question, answer='', sources=[], ok=False, error='Sem evidência institucional.')
            return {
                'ok': True,
                'answer': 'Não encontrei informação suficiente nas bases institucionais liberadas para o seu perfil. A dúvida foi registrada para revisão.',
                'sources': [],
                'grounded': False,
            }

        evidence_text = []
        sources = []
        for e in evidence:
            citation = f"[KB:{e['collection']}/doc:{e.get('document_id')}/chunk:{e.get('chunk_id')}]"
            evidence_text.append(
                f"{citation}\nTítulo: {e.get('title')}\nFonte: {e.get('source')}\nTrecho: {e.get('text')}"
            )
            sources.append({**e, 'citation': citation})

        prompt = (
            'Você é o assistente interno do SindPetshop-SP. Responda em português, de forma clara e profissional. '
            'Use SOMENTE as evidências abaixo. Não complete lacunas com conhecimento externo. '
            'Quando uma afirmação depender de uma evidência, inclua a citação fornecida. '
            'Se as evidências forem insuficientes, diga explicitamente.\n\n'
            f'PERGUNTA:\n{question}\n\nEVIDÊNCIAS:\n' + '\n\n'.join(evidence_text)
        )

        started = time.monotonic()
        try:
            timeout = int(settings.get('answer_timeout_seconds', '45'))
            response = requests.post(
                (self.ollama_url if self.ollama_url.endswith('/api/chat') else self.ollama_url + '/api/chat'),
                json={
                    'model': self.model,
                    'stream': False,
                    'think': False,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'options': {'temperature': 0.1, 'num_ctx': 4096},
                },
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()
            answer = ((data.get('message') or {}).get('content') or '').strip()
            if not answer:
                raise RuntimeError('Modelo retornou resposta vazia.')
            latency = (time.monotonic() - started) * 1000
            self.team.ask_log_add(user.get('id'), question, answer=answer, sources=sources, ok=True, latency_ms=latency)
            return {'ok': True, 'answer': answer, 'sources': sources, 'grounded': True, 'latency_ms': round(latency, 1)}
        except Exception as exc:
            fallback = 'Encontrei os seguintes trechos institucionais relacionados:\n\n'
            for e in sources[:4]:
                fallback += f"{e['citation']} {e.get('title')}\n{e.get('text', '')[:500]}\n\n"
            fallback += 'A síntese automática não foi concluída. Consulte os trechos acima ou peça revisão interna.'
            latency = (time.monotonic() - started) * 1000
            self.team.ask_log_add(user.get('id'), question, answer=fallback, sources=sources, ok=False, latency_ms=latency, error=str(exc))
            return {'ok': True, 'answer': fallback, 'sources': sources, 'grounded': True, 'fallback': True, 'error': str(exc)}

    def dashboard(self, user):
        return {
            'ok': True,
            'user': user,
            'collections': self.allowed_collections(user),
            'tracks': self.allowed_tracks(user),
            'stats': self.team.stats(),
        }


HTML = r'''<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sind Assist</title>
<style>
:root{--bg:#08090f;--panel:#0e1019;--panel2:#111422;--line:#23283a;--text:#f4f5fa;--muted:#8990aa;--violet:#6d5dfc;--green:#27d39d}
*{box-sizing:border-box}body{margin:0;font-family:Inter,Segoe UI,Arial;background:var(--bg);color:var(--text);height:100vh}.app{height:100vh;display:grid;grid-template-columns:230px 1fr}.side{border-right:1px solid var(--line);padding:22px;background:#090a10}.brand{font-weight:700;font-size:20px;margin-bottom:28px}.brand b{color:var(--violet)}.nav{display:grid;gap:8px}.nav button{border:0;background:transparent;color:var(--muted);padding:12px;border-radius:10px;text-align:left;cursor:pointer}.nav button.active,.nav button:hover{background:var(--panel2);color:var(--text)}.main{display:grid;grid-template-rows:64px 1fr 90px}.top{border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 24px;justify-content:space-between}.status{font-size:12px;color:var(--green)}.content{padding:30px;overflow:auto;max-width:980px;width:100%;margin:auto}.msg{margin:0 0 22px}.who{font-size:12px;font-weight:700;margin-bottom:6px}.bubble{font-size:14px;line-height:1.65;color:#d8dbea;white-space:pre-wrap}.sources{margin-top:12px;display:grid;gap:7px}.source{font-size:11px;color:var(--muted);border-left:2px solid var(--violet);padding-left:9px}.composer{border-top:1px solid var(--line);padding:14px 24px}.box{max-width:980px;margin:auto;display:flex;gap:10px;background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:10px}.box textarea{flex:1;resize:none;background:transparent;border:0;outline:0;color:var(--text);font:inherit;min-height:42px}.box button{width:48px;border:0;border-radius:10px;background:var(--violet);color:white;cursor:pointer}.card{border:1px solid var(--line);background:var(--panel);border-radius:14px;padding:16px;margin-bottom:12px}.muted{color:var(--muted);font-size:12px}.login{width:360px;max-width:90vw;margin:15vh auto}.login input{width:100%;margin:6px 0;padding:12px;border-radius:9px;border:1px solid var(--line);background:var(--panel);color:white}.login button{width:100%;padding:12px;margin-top:10px;background:var(--violet);border:0;border-radius:9px;color:white}.hidden{display:none!important}
</style>
</head>
<body>
<div id="login" class="login"><div class="brand"><b>✦</b> Sind Assist</div><div class="card"><div style="font-weight:700;margin-bottom:10px">Acesso da equipe</div><input id="user" placeholder="Usuário"><input id="pass" type="password" placeholder="Senha"><button onclick="loginNow()">Entrar</button><div id="loginErr" class="muted" style="margin-top:10px"></div></div></div>
<div id="app" class="app hidden"><aside class="side"><div class="brand"><b>✦</b> Sind Assist</div><div class="nav"><button class="active" onclick="showChat(this)">Assistente</button><button onclick="showKnowledge(this)">Conhecimento</button><button onclick="showTraining(this)">Treinamento</button><button onclick="showProfile(this)">Meu perfil</button><button onclick="logoutNow()">Sair</button></div></aside><main class="main"><header class="top"><div><b id="title">Assistente institucional</b><div class="muted" id="subtitle">Respostas baseadas em materiais internos</div></div><div class="status">● Local</div></header><section id="content" class="content"></section><section id="composer" class="composer"><div class="box"><textarea id="q" placeholder="Pergunte sobre procedimentos, CCTs, treinamento..."></textarea><button onclick="askNow()">↑</button></div></section></main></div>
<script>
const API='';let token=localStorage.getItem('sind_token')||'';let dashboard=null;
async function req(path,opt={}){opt.headers={...(opt.headers||{}),'Content-Type':'application/json',...(token?{'Authorization':'Bearer '+token}:{})};let r=await fetch(API+path,opt);let d=await r.json();if(r.status===401){localStorage.removeItem('sind_token');if(path!='/api/login')location.reload()}return d}
async function loginNow(){let d=await req('/api/login',{method:'POST',body:JSON.stringify({username:user.value,password:pass.value})});if(!d.ok){loginErr.textContent=d.error||'Falha';return}token=d.token;localStorage.setItem('sind_token',token);boot()}
function logoutNow(){req('/api/logout',{method:'POST'});localStorage.removeItem('sind_token');location.reload()}
function nav(btn){document.querySelectorAll('.nav button').forEach(x=>x.classList.remove('active'));btn.classList.add('active')}
async function boot(){if(!token)return;let d=await req('/api/dashboard');if(!d.ok)return;dashboard=d;login.classList.add('hidden');app.classList.remove('hidden');showChat(document.querySelector('.nav button'))}
function showChat(btn){nav(btn);title.textContent='Assistente institucional';subtitle.textContent='Respostas fundamentadas na base liberada para seu perfil';composer.classList.remove('hidden');content.innerHTML='<div class="card"><b>Olá, '+esc(dashboard.user.display_name)+'</b><div class="muted" style="margin-top:6px">Pergunte sobre materiais, procedimentos ou treinamentos disponíveis.</div></div>'}
function showKnowledge(btn){nav(btn);title.textContent='Conhecimento';subtitle.textContent='Coleções liberadas para seu perfil';composer.classList.add('hidden');content.innerHTML=(dashboard.collections||[]).map(x=>'<div class="card"><b>'+esc(x)+'</b><div class="muted">Base institucional disponível para consulta</div></div>').join('')||'<div class="card muted">Nenhuma coleção liberada.</div>'}
function showTraining(btn){nav(btn);title.textContent='Treinamento';subtitle.textContent='Trilhas liberadas';composer.classList.add('hidden');content.innerHTML=(dashboard.tracks||[]).map(x=>'<div class="card"><b>'+esc(x.name)+'</b><div class="muted">'+esc(x.description||'')+'</div></div>').join('')||'<div class="card muted">Nenhuma trilha liberada.</div>'}
function showProfile(btn){nav(btn);title.textContent='Meu perfil';subtitle.textContent='Permissões locais';composer.classList.add('hidden');let u=dashboard.user;content.innerHTML='<div class="card"><b>'+esc(u.display_name)+'</b><div class="muted">@'+esc(u.username)+' • '+esc(u.role_name||'sem função')+'</div></div>'}
async function askNow(){let text=q.value.trim();if(!text)return;q.value='';content.innerHTML+='<div class="msg"><div class="who">Você</div><div class="bubble">'+esc(text)+'</div></div><div id="wait" class="muted">Jarvis está consultando as bases...</div>';content.scrollTop=content.scrollHeight;let d=await req('/api/ask',{method:'POST',body:JSON.stringify({question:text})});let w=document.getElementById('wait');if(w)w.remove();let src=(d.sources||[]).map(x=>'<div class="source">'+esc(x.citation||'')+' '+esc(x.title||'')+'</div>').join('');content.innerHTML+='<div class="msg"><div class="who">Jarvis</div><div class="bubble">'+esc(d.answer||d.error||'Sem resposta')+'</div><div class="sources">'+src+'</div></div>';content.scrollTop=content.scrollHeight}
function esc(s){return String(s??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
if(token)boot();
</script>
</body></html>'''


def build_handler(app):
    class Handler(BaseHTTPRequestHandler):
        server_version = 'SindAssist/0.9'
        def log_message(self, fmt, *args): pass

        def _json(self, status, payload):
            raw = json.dumps(payload, ensure_ascii=False, default=str).encode('utf-8')
            self.send_response(status); self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(raw))); self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers(); self.wfile.write(raw)

        def _body(self):
            n = int(self.headers.get('Content-Length', '0') or 0)
            if n > 1024 * 1024: raise ValueError('Payload grande demais.')
            raw = self.rfile.read(n) if n else b'{}'
            return json.loads(raw.decode('utf-8') or '{}')

        def _token(self):
            auth = self.headers.get('Authorization', '')
            return auth[7:].strip() if auth.startswith('Bearer ') else ''

        def _user(self): return app.session(self._token())

        def do_GET(self):
            path = urlparse(self.path).path
            if path == '/':
                raw = HTML.encode('utf-8'); self.send_response(200); self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(raw))); self.end_headers(); self.wfile.write(raw); return
            user = self._user()
            if not user: return self._json(401, {'ok': False, 'error': 'Não autenticado.'})
            if path == '/api/dashboard': return self._json(200, app.dashboard(user))
            if path == '/api/collections': return self._json(200, {'ok': True, 'items': app.allowed_collections(user)})
            if path == '/api/tracks': return self._json(200, {'ok': True, 'items': app.allowed_tracks(user)})
            return self._json(404, {'ok': False, 'error': 'Rota não encontrada.'})

        def do_POST(self):
            path = urlparse(self.path).path
            try: body = self._body()
            except Exception as exc: return self._json(400, {'ok': False, 'error': str(exc)})
            if path == '/api/login':
                result = app.team.authenticate(body.get('username', ''), body.get('password', ''))
                if not result.get('ok'): return self._json(401, result)
                token = app.create_session(result['user'])
                return self._json(200, {'ok': True, 'token': token, 'user': result['user']})
            user = self._user()
            if not user: return self._json(401, {'ok': False, 'error': 'Não autenticado.'})
            if path == '/api/logout': app.logout(self._token()); return self._json(200, {'ok': True})
            if path == '/api/ask':
                question = str(body.get('question', '')).strip()
                if not question: return self._json(400, {'ok': False, 'error': 'Pergunta vazia.'})
                return self._json(200, app.answer(user, question))
            if path == '/api/feedback':
                result = app.team.feedback_add(user.get('id'), body.get('rating'), body.get('category', 'portal'), body.get('question', ''), body.get('answer', ''), body.get('comment', ''))
                return self._json(200, result)
            return self._json(404, {'ok': False, 'error': 'Rota não encontrada.'})
    return Handler


def run_portal(persistent_root, release_root):
    persistent_root = Path(persistent_root)
    team = TeamAssistantEngine(persistent_root / 'team' / 'team.db')
    knowledge = KnowledgeBase(persistent_root / 'knowledge' / 'knowledge.db', persistent_root / 'knowledge' / 'storage')
    training = TrainingEngine(persistent_root / 'training' / 'training.db', knowledge_engine=None)
    config = json.loads((Path(release_root) / 'data' / 'config.json').read_text(encoding='utf-8'))
    settings = {x['key']: x['value'] for x in team.setting_get().get('items', [])}
    host = settings.get('portal_host', '127.0.0.1'); port = int(settings.get('portal_port', '8765'))
    if host == '0.0.0.0': print('ATENÇÃO: portal exposto na rede local. Use firewall e senhas fortes.')
    app = TeamPortalApp(team, knowledge, training, config.get('ollama_url', 'http://127.0.0.1:11434'), config.get('model', 'qwen3:4b'))
    server = ThreadingHTTPServer((host, port), build_handler(app))
    print(f'Sind Assist ativo em http://{host}:{port}')
    print('Pressione Ctrl+C para encerrar.')
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
