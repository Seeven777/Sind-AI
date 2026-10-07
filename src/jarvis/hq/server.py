from __future__ import annotations

import asyncio
import json
import hmac
import ipaddress
import secrets
import socket
from concurrent.futures import Future
import mimetypes
import threading
import urllib.error
import urllib.request
import webbrowser
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote
from jarvis import __version__

from jarvis.app.product_runtime import start_product_runtime
from jarvis.voice import VoiceUnavailable


class _State:
    def __init__(self, runtime, loop, *, allow_remote=False, access_token=None, port=4760):
        self.runtime = runtime
        self.loop = loop
        self.allow_remote = bool(allow_remote)
        self.access_token = str(access_token or "")
        self.port = int(port)
        self.lan_ip = _lan_ip() if self.allow_remote else "127.0.0.1"

    def call(self, coro, timeout=900):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)

    def call_sync(self, func, *args, timeout=900, **kwargs):
        """Run synchronous runtime work on Jarvis' owner event-loop thread.

        The local UI uses ThreadingHTTPServer, so request handlers run in worker
        threads. Jarvis' SQLite connection is deliberately owned by the runtime
        thread; executing repository/service methods from an HTTP worker would
        violate sqlite3's same-thread contract. Queueing the callable onto the
        owner loop keeps SQLite thread affinity intact without weakening SQLite's
        safety checks with check_same_thread=False.
        """
        future = Future()

        def invoke():
            if future.cancelled():
                return
            try:
                future.set_result(func(*args, **kwargs))
            except BaseException as exc:
                future.set_exception(exc)

        self.loop.call_soon_threadsafe(invoke)
        return future.result(timeout=timeout)




def _is_loopback(address: str) -> bool:
    try:
        return ipaddress.ip_address(str(address)).is_loopback
    except ValueError:
        return str(address).lower() in {"localhost", "::1"}


def _lan_ip() -> str:
    """Best-effort LAN address without making an HTTP request."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        value = str(sock.getsockname()[0])
        if value and not value.startswith("127."):
            return value
    except OSError:
        pass
    finally:
        sock.close()
    try:
        for value in socket.gethostbyname_ex(socket.gethostname())[2]:
            if value and not value.startswith("127."):
                return value
    except OSError:
        pass
    return "127.0.0.1"


def _mobile_access_token(runtime) -> str:
    key = "mobile_access_token"
    token = runtime.secret_store.get(key)
    if token:
        return str(token)
    token = secrets.token_urlsafe(32)
    runtime.secret_store.set(key, token)
    return token


def _assets_root() -> Path:
    return Path(__file__).resolve().parents[1] / "ui" / "hq_web"


def ui_server_alive(host: str = "127.0.0.1", port: int = 4760, timeout: float = 1.5) -> bool:
    """Cheap liveness check that never touches Ollama or other optional providers."""
    url = f"http://{host}:{port}/api/ping"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return False
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("service") == "jarvis-ui" and payload.get("ok") is True
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return False


def _handler(state: _State):
    assets = _assets_root()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def _send(self, status, body, content_type="application/json; charset=utf-8"):
            if isinstance(body, (dict, list)):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json_body(self):
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0:
                return {}
            return json.loads(self.rfile.read(length).decode("utf-8"))

        def _request_is_local(self):
            """Return True only for a direct localhost request.

            Reverse proxies (Tailscale Funnel, Cloudflare Tunnel, etc.) connect
            to Jarvis through localhost, so ``client_address`` alone is not a
            trustworthy signal.  A public Host or forwarding header always
            turns the request into a remote request and therefore requires the
            mobile access token/session.
            """
            forwarded = str(
                self.headers.get("CF-Connecting-IP")
                or self.headers.get("X-Forwarded-For")
                or ""
            ).split(",", 1)[0].strip()
            if forwarded and not _is_loopback(forwarded):
                return False

            host = str(self.headers.get("Host") or "").strip().lower()
            host_name = host
            if host.startswith("[") and "]" in host:
                host_name = host[1:host.index("]")]
            elif ":" in host:
                host_name = host.rsplit(":", 1)[0]
            if host_name and host_name not in {"localhost", "127.0.0.1", "::1"}:
                return False
            return _is_loopback(self.client_address[0])

        def _request_is_https(self):
            proto = str(self.headers.get("X-Forwarded-Proto") or "").lower().strip()
            if proto == "https":
                return True
            host = str(self.headers.get("Host") or "").lower()
            return host.endswith(".ts.net") or ".ts.net:" in host or host.endswith(".trycloudflare.com") or ".trycloudflare.com:" in host

        def _remote_authorized(self, *, establish_session=False):
            # Desktop localhost remains frictionless. LAN/mobile access requires
            # a secret generated once and protected by the Windows secret store.
            if self._request_is_local():
                return True
            if not state.allow_remote or not state.access_token:
                self._send(403, {"error": "mobile access disabled"})
                return False

            parsed = urlparse(self.path)
            supplied = str((parse_qs(parsed.query).get("token") or [""])[0])
            cookie = SimpleCookie(self.headers.get("Cookie", ""))
            session = cookie.get("jarvis_mobile_session")
            cookie_value = session.value if session else ""
            valid_query = bool(supplied) and hmac.compare_digest(supplied, state.access_token)
            valid_cookie = bool(cookie_value) and hmac.compare_digest(cookie_value, state.access_token)
            if valid_cookie:
                return True
            if valid_query and establish_session:
                clean = parsed.path or "/"
                if parsed.fragment:
                    clean += "#" + parsed.fragment
                self.send_response(302)
                self.send_header("Location", clean)
                self.send_header(
                    "Set-Cookie",
                    f"jarvis_mobile_session={state.access_token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=2592000"
                    + ("; Secure" if self._request_is_https() else ""),
                )
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                return False
            if valid_query:
                return True
            self._send(401, {"error": "mobile authorization required"})
            return False

        def do_GET(self):
            if not self._remote_authorized(establish_session=True):
                return
            path = urlparse(self.path).path
            if path == "/api/ping":
                return self._send(200, {
                    "ok": True,
                    "service": "jarvis-ui",
                    "run_id": state.call_sync(lambda: state.runtime.foundation.run_id),
                })
            if path == "/api/mobile":
                local = self._request_is_local()
                payload = {
                    "enabled": state.allow_remote,
                    "lan_ip": state.lan_ip,
                    "port": state.port,
                    "url": f"http://{state.lan_ip}:{state.port}/",
                }
                if local and state.allow_remote:
                    payload["connect_url"] = f"http://{state.lan_ip}:{state.port}/mobile?token={state.access_token}"
                    payload["desktop_connect_url"] = f"http://{state.lan_ip}:{state.port}/?token={state.access_token}"
                    payload["access_token"] = state.access_token
                return self._send(200, payload)
            if path == "/api/conversations":
                query=parse_qs(urlparse(self.path).query)
                search=str((query.get("search") or [""])[0])
                include_archived=str((query.get("archived") or ["0"])[0]).lower() in {"1","true","yes"}
                rows=state.call_sync(state.runtime.chat.list_conversations,search=search,limit=100,include_archived=include_archived)
                return self._send(200, rows)
            if path.startswith("/api/conversations/") and path.endswith("/export"):
                parts=path.split("/")
                cid=unquote(parts[3] if len(parts)>3 else "")
                query=parse_qs(urlparse(self.path).query)
                fmt=str((query.get("format") or ["md"])[0]).lower()
                try:
                    exported=state.call_sync(state.runtime.chat.export_conversation,cid,fmt)
                except KeyError:
                    return self._send(404,{"error":"conversation not found"})
                if fmt=="json":
                    return self._send(200,exported)
                return self._send(200,exported,"text/markdown; charset=utf-8")
            if path.startswith("/api/conversations/"):
                cid=unquote(path.split("/",3)[3] if len(path.split("/",3))>3 else "")
                try:
                    convo=state.call_sync(state.runtime.chat.get_conversation,cid)
                except Exception:
                    convo=None
                if convo is None:
                    return self._send(404,{"error":"conversation not found"})
                return self._send(200, convo)
            if path == "/api/hq":
                return self._send(200, state.call_sync(state.runtime.hq.snapshot))
            if path == "/api/briefing":
                return self._send(200, state.call_sync(state.runtime.briefing.snapshot))
            if path == "/api/meta":
                return self._send(200, state.call_sync(lambda: {
                    "name": "Jarvis", "version": __version__,
                    "privacy_mode": state.runtime.foundation.config.privacy.mode,
                    "default_model": state.runtime.model_router.default_model,
                    "default_provider": state.runtime.model_router.default_provider,
                    "premium_provider": state.runtime.model_router.premium_provider,
                    "ai_mesh": state.runtime.ai_mesh.health(),
                }))
            if path == "/api/preferences":
                return self._send(200, state.call_sync(state.runtime.preferences.all))
            if path == "/api/models":
                return self._send(200, state.call_sync(lambda: state.runtime.model_registry.health()))
            if path == "/api/health":
                return self._send(200, state.call_sync(lambda: {
                    "foundation": state.runtime.foundation.health.snapshot(),
                    "privacy": {"mode": state.runtime.foundation.config.privacy.mode},
                    "models": state.runtime.model_registry.health(),
                    "connectors": state.runtime.connectors.health(),
                }))
            if path == "/api/ai-mesh":
                return self._send(200, state.call_sync(state.runtime.ai_mesh.health))
            if path == "/api/connectors":
                return self._send(200, state.call_sync(lambda: {
                    "health": state.runtime.connectors.health(),
                    "sources": state.runtime.connector_repository.sources(),
                    "counts": state.runtime.connector_repository.counts(),
                }))
            if path == "/api/watchers":
                return self._send(200, state.call_sync(state.runtime.watcher_repository.enabled))
            if path == "/api/system":
                return self._send(200, state.call_sync(lambda: {
                    "foundation": state.runtime.foundation.health.snapshot(),
                    "models": state.runtime.model_registry.health(),
                    "ai_mesh": state.runtime.ai_mesh.health(),
                    "connectors": state.runtime.connectors.health(),
                    "browser": state.runtime.browser.health(),
                    "windows": state.runtime.windows.health(),
                    "voice": state.runtime.voice.health(),
                    "internet": {
                        "status": "healthy" if {"web.search", "web.fetch"}.issubset(set(state.runtime.tool_registry.list_ids())) else "disabled",
                        "mode": "read_only",
                        "tools": [x for x in state.runtime.tool_registry.list_ids() if x.startswith("web.") or x.startswith("browser.")],
                    },
                    "mcp": state.runtime.mcp.health(),
                    "a2a": state.runtime.a2a.health(),
                    "nodes": state.runtime.nodes.repository.list(),
                    "skills": state.runtime.skill_manager.repository.list(),
                    "capabilities": state.runtime.capabilities.inventory(),
                    "scheduler": state.runtime.scheduler_repository.all(),
                    "watchers": state.runtime.watcher_repository.enabled(),
                    "google": state.runtime.google_oauth.status(),
                }))
            if path == "/api/voice/health":
                return self._send(200, state.call_sync(state.runtime.voice.health))
            if path == "/api/voice/diagnostics":
                return self._send(200, state.call_sync(state.runtime.voice.diagnostics))
            if path == "/api/projects":
                return self._send(200, state.call_sync(state.runtime.projects.list))
            if path == "/api/skills":
                return self._send(200, state.call_sync(state.runtime.skill_manager.repository.list))
            if path == "/api/capabilities":
                return self._send(200, state.call_sync(state.runtime.capabilities.inventory))
            if path == "/api/opportunities":
                return self._send(200, state.call_sync(state.runtime.opportunities.scan))
            if path == "/api/autonomy":
                return self._send(200, state.call_sync(state.runtime.autonomy.status))
            if path == "/api/attention":
                return self._send(200, state.call_sync(lambda: state.runtime.autonomy_repository.notifications(limit=30)))
            if path == "/api/improvements":
                return self._send(200, state.call_sync(lambda: state.runtime.autonomy_repository.proposals(limit=40)))
            if path == "/api/tool-runs":
                return self._send(200, state.call_sync(state.runtime.tool_runs.recent, 50))
            if path == "/api/events":
                return self._send(200, state.call_sync(state.runtime.foundation.events.recent, 100))
            if path == "/api/memory":
                return self._send(200, state.call_sync(state.runtime.memory.repository.recent, 100))
            if path == "/api/agents":
                return self._send(200, state.call_sync(state.runtime.hq.agent_directory))
            if path == "/api/agency":
                return self._send(200, state.call_sync(lambda: {
                    "status": state.runtime.agency_catalog.status(),
                    "router": state.runtime.agent_router.status(),
                    "runbooks": [
                        {
                            "slug": x.get("slug"), "title": x.get("title"),
                            "mode": x.get("mode"), "duration": x.get("duration"),
                            "summary": x.get("summary"),
                        } for x in state.runtime.agency_catalog.runbooks()
                    ],
                }))
            if path == "/api/google/status":
                return self._send(200, state.call_sync(state.runtime.google_oauth.status))
            if path == "/":
                target = assets / "companion.html"
            elif path == "/mobile":
                target = assets / "mobile.html"
            elif path in {"/hq", "/office"}:
                target = assets / "index.html"
            elif path == "/hq-classic":
                target = assets / "hq-classic.html"
            elif path == "/mission-control":
                target = assets / "mission-control.html"
            elif path == "/system":
                target = assets / "system.html"
            elif path == "/projects":
                target = assets / "projects.html"
            elif path == "/memory":
                target = assets / "memory.html"
            elif path == "/agents":
                target = assets / "agents.html"
            else:
                relative = path.lstrip("/")
                if ".." in Path(relative).parts:
                    return self._send(403, b"forbidden", "text/plain")
                target = assets / relative
            if not target.exists() or not target.is_file():
                return self._send(404, b"not found", "text/plain")
            ctype, _ = mimetypes.guess_type(target.name)
            return self._send(200, target.read_bytes(), ctype or "application/octet-stream")

        def do_POST(self):
            if not self._remote_authorized():
                return
            path = urlparse(self.path).path
            try:
                payload = self._json_body()
                if path == "/api/conversations":
                    title=str(payload.get("title") or "Nova conversa")
                    cid=state.call_sync(state.runtime.chat.new_conversation,title)
                    return self._send(201,{"conversation_id":cid,"conversation":state.call_sync(state.runtime.chat.get_conversation,cid)})
                if path.startswith("/api/conversations/"):
                    cid=unquote(path.split("/",3)[3] if len(path.split("/",3))>3 else "")
                    action=str(payload.get("action") or "")
                    if action=="rename":
                        convo=state.call_sync(state.runtime.chat.rename_conversation,cid,str(payload.get("title") or "Nova conversa"))
                        return self._send(200,convo)
                    if action=="pin":
                        convo=state.call_sync(state.runtime.chat.set_conversation_flags,cid,pinned=bool(payload.get("value")))
                        return self._send(200,convo)
                    if action=="archive":
                        convo=state.call_sync(state.runtime.chat.set_conversation_flags,cid,archived=bool(payload.get("value")))
                        return self._send(200,convo)
                    if action=="regenerate":
                        mode=str(payload.get("mode") or "auto").lower().strip()
                        if mode not in {"auto","fast","deep","hermes"}:
                            return self._send(400,{"error":"mode inválido"})
                        result=state.call(state.runtime.chat.regenerate(cid,mode=mode))
                        result["conversation_id"]=cid
                        return self._send(200,result)
                    return self._send(400,{"error":"ação de conversa desconhecida"})
                if path == "/api/chat":
                    cid = payload.get("conversation_id")
                    if not cid:
                        cid = state.call_sync(state.runtime.chat.new_conversation)
                    text = str(payload.get("text") or "").strip()
                    if not text:
                        return self._send(400, {"error": "text obrigatório"})
                    mode = str(payload.get("mode") or "auto").lower().strip()
                    if mode not in {"auto","fast","deep","hermes"}:
                        return self._send(400, {"error": "mode inválido"})
                    attachments = payload.get("attachments") or []
                    if not isinstance(attachments, list) or len(attachments) > 3:
                        return self._send(400, {"error": "máximo de 3 anexos"})
                    safe_attachments=[]
                    for item in attachments:
                        if not isinstance(item, dict):
                            return self._send(400,{"error":"anexo inválido"})
                        name=str(item.get("name") or "arquivo")[:160]
                        content=str(item.get("content") or "")
                        if len(content) > 800_000:
                            return self._send(413,{"error":f"anexo excede o limite: {name}"})
                        safe_attachments.append({"name":name,"content":content})
                    result = state.call(state.runtime.chat.send(cid, text, mode=mode, attachments=safe_attachments))
                    result["conversation_id"] = cid
                    return self._send(200, result)
                if path == "/api/voice/synthesize":
                    text = str(payload.get("text") or "").strip()
                    if not text:
                        return self._send(400, {"error": "text obrigatório"})
                    try:
                        audio_path = state.call_sync(state.runtime.voice.synthesize, text, timeout=240)
                        audio_file = Path(audio_path)
                        audio = audio_file.read_bytes()
                        content_type = "audio/mpeg" if audio_file.suffix.lower() == ".mp3" else "audio/wav"
                        try:
                            audio_file.unlink(missing_ok=True)
                        except Exception:
                            pass
                        return self._send(200, audio, content_type)
                    except VoiceUnavailable as exc:
                        return self._send(503, {"error": str(exc), "fallback": "web-speech"})
                if path == "/api/voice/speak-native":
                    text = str(payload.get("text") or "").strip()
                    if not text:
                        return self._send(400, {"error": "text obrigatório"})
                    try:
                        state.call_sync(state.runtime.voice.speak_native, text, timeout=240)
                        return self._send(200, {"status": "spoken", "backend": "windows-sapi"})
                    except VoiceUnavailable as exc:
                        return self._send(503, {"error": str(exc)})
                if path == "/api/voice/test":
                    text = str(payload.get("text") or "Estou ouvindo, senhor.").strip()
                    try:
                        state.call_sync(state.runtime.voice.speak_native, text, timeout=240)
                        return self._send(200, {
                            "status": "spoken", "backend": "windows-sapi",
                            "diagnostics": state.call_sync(state.runtime.voice.diagnostics)
                        })
                    except VoiceUnavailable as exc:
                        return self._send(503, {
                            "error": str(exc), "diagnostics": state.call_sync(state.runtime.voice.diagnostics)
                        })
                if path == "/api/preferences":
                    values=payload.get("preferences") if isinstance(payload.get("preferences"),dict) else payload
                    result=state.call_sync(state.runtime.preferences.update,values)
                    return self._send(200,result)
                if path == "/api/memory":
                    content=str(payload.get("content") or "").strip()
                    if not content:
                        return self._send(400,{"error":"content obrigatório"})
                    mid=state.call_sync(
                        state.runtime.memory.remember,
                        content,
                        memory_type=str(payload.get("memory_type") or "semantic"),
                        source="user",
                        scope=str(payload.get("scope") or "global"),
                        importance=float(payload.get("importance") or .7),
                        metadata=payload.get("metadata") or {},
                    )
                    return self._send(201,{"memory_id":mid,"created":True})
                if path == "/api/mission/team":
                    objective = str(payload.get("objective") or "").strip()
                    if not objective:
                        return self._send(400, {"error": "objective obrigatório"})
                    result = state.call(
                        state.runtime.missions.run(
                            objective,
                            title=payload.get("title") or "Missão em equipe",
                        )
                    )
                    return self._send(200, result)
                if path.startswith("/api/approval/") and path.endswith("/approve"):
                    approval_id = path.split("/")[3]
                    operator = state.call_sync(state.runtime.agent_registry.runtime, "operations.operator")
                    result = state.call(operator.resume_approval(approval_id))
                    return self._send(200, result)
                if path.startswith("/api/approval/") and path.endswith("/reject"):
                    approval_id = path.split("/")[3]
                    operator = state.call_sync(state.runtime.agent_registry.runtime, "operations.operator")
                    result = state.call(operator.reject_approval(approval_id))
                    return self._send(200, result)
                if path == "/api/connectors/sync":
                    result = state.call(state.runtime.connectors.sync_all())
                    state.call(state.runtime.watchers.check_all())
                    return self._send(200, result)
                if path == "/api/scheduler/tick":
                    result = state.call(state.runtime.scheduler.run_due())
                    return self._send(200, result)
                if path == "/api/autonomy/tick":
                    result = state.call(state.runtime.autonomy.tick(force=bool(payload.get("force", True)), scope=payload.get("scope")), timeout=1200)
                    return self._send(200, result)
                if path.startswith("/api/attention/") and path.endswith("/ack"):
                    notification_id=unquote(path.split("/")[3])
                    result=state.call_sync(state.runtime.autonomy.acknowledge,notification_id)
                    return self._send(200,result)
                if path.startswith("/api/improvements/") and path.endswith("/approve"):
                    proposal_id=unquote(path.split("/")[3])
                    result=state.call(state.runtime.autonomy.approve_improvement(proposal_id))
                    return self._send(200,result)
                if path.startswith("/api/improvements/") and path.endswith("/reject"):
                    proposal_id=unquote(path.split("/")[3])
                    result=state.call(state.runtime.autonomy.reject_improvement(proposal_id))
                    return self._send(200,result)
                if path == "/api/project":
                    name = str(payload.get("name") or "").strip()
                    if not name:
                        return self._send(400, {"error": "name obrigatório"})
                    result = state.call_sync(
                        state.runtime.projects.create,
                        name,
                        str(payload.get("objective") or ""),
                        state.call_sync(state.runtime.workspace.get, "workspace_id"),
                        payload.get("metadata") or {},
                    )
                    return self._send(200, result)
                if path == "/api/google/auth":
                    result = state.call(asyncio.to_thread(
                        state.runtime.google_oauth.authenticate_interactive,
                        True, 240
                    ), timeout=270)
                    state.call(state.runtime.connectors.sync_all())
                    return self._send(200, {
                        "status": "authorized",
                        "scope": result.get("scope"),
                        "has_refresh_token": bool(result.get("refresh_token")),
                    })
                if path == "/api/google/disconnect":
                    state.call_sync(state.runtime.google_oauth.token_store.delete)
                    return self._send(200, {"status": "disconnected"})
                if path == "/api/skill/scaffold":
                    skill_id = str(payload.get("skill_id") or "").strip()
                    if not skill_id:
                        return self._send(400, {"error": "skill_id obrigatório"})
                    result = state.call_sync(
                        state.runtime.skill_manager.create_scaffold,
                        skill_id,
                        str(payload.get("description") or "Skill Jarvis"),
                        tuple(payload.get("capabilities") or ()),
                    )
                    return self._send(200, result)
                return self._send(404, {"error": "not found"})
            except Exception as exc:
                return self._send(500, {"error": str(exc)})

        def do_DELETE(self):
            if not self._remote_authorized():
                return
            path=urlparse(self.path).path
            try:
                if path.startswith("/api/memory/"):
                    mid=unquote(path.split("/",3)[3] if len(path.split("/",3))>3 else "")
                    ok=state.call_sync(state.runtime.memory.repository.delete,mid)
                    if not ok: return self._send(404,{"error":"memory not found"})
                    return self._send(200,{"memory_id":mid,"deleted":True})
                if path.startswith("/api/conversations/"):
                    cid=unquote(path.split("/",3)[3] if len(path.split("/",3))>3 else "")
                    result=state.call_sync(state.runtime.chat.delete_conversation,cid)
                    return self._send(200,result)
                return self._send(404,{"error":"not found"})
            except KeyError:
                return self._send(404,{"error":"conversation not found"})
            except Exception as exc:
                return self._send(500,{"error":str(exc)})

    return Handler


async def serve_hq(
    data_dir=None,
    *,
    host="127.0.0.1",
    port=4760,
    open_browser=True,
    start_page="/",
    allow_remote=False,
):
    bind_host = "0.0.0.0" if allow_remote else host
    local_url = f"http://127.0.0.1:{port}{start_page}"

    # A second launcher must reuse the existing Jarvis process instead of
    # creating a competing ProductRuntime and tripping the single-instance lock.
    if ui_server_alive("127.0.0.1", port):
        print(f"Jarvis já está ativo. Reutilizando: {local_url}")
        if open_browser:
            webbrowser.open(local_url)
        return

    runtime = await start_product_runtime(data_dir)
    loop = asyncio.get_running_loop()
    access_token = _mobile_access_token(runtime) if allow_remote else None
    state = _State(runtime, loop, allow_remote=allow_remote, access_token=access_token, port=port)

    async def background_services():
        # Scheduler and the autonomous life loop share the runtime owner thread,
        # preserving SQLite affinity while keeping the HTTP UI responsive.
        await asyncio.sleep(2)
        while True:
            try:
                await runtime.scheduler.run_due()
            except Exception:
                pass
            try:
                await runtime.autonomy.tick()
            except Exception:
                pass
            await asyncio.sleep(30)

    background_task = asyncio.create_task(
        background_services(),
        name="jarvis-background-services",
    )
    server = ThreadingHTTPServer((bind_host, port), _handler(state))
    thread = threading.Thread(
        target=server.serve_forever,
        name="jarvis-local-ui",
        daemon=True,
    )
    thread.start()
    print(f"Jarvis local UI: {local_url}")
    print(f"Companion: http://127.0.0.1:{port}/")
    print(f"HQ:        http://127.0.0.1:{port}/hq")
    print(f"Missões:   http://127.0.0.1:{port}/mission-control")
    print(f"Projetos:  http://127.0.0.1:{port}/projects")
    print(f"Agentes:   http://127.0.0.1:{port}/agents")
    print(f"Memória:   http://127.0.0.1:{port}/memory")
    print(f"Sistema:   http://127.0.0.1:{port}/system")
    if allow_remote:
        print(f"Mobile:    http://{state.lan_ip}:{port}/?token={access_token}")
    print("Ctrl+C para fechar.")
    if open_browser:
        webbrowser.open(local_url)
    try:
        while True:
            await asyncio.sleep(1)
    finally:
        background_task.cancel()
        try:
            await background_task
        except asyncio.CancelledError:
            pass
        server.shutdown()
        server.server_close()
        await runtime.close()
