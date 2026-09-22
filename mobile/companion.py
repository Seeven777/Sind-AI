import base64
import json
import mimetypes
import ipaddress
import secrets
import socket
import subprocess
import threading
import time
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


class MobileCompanion:
    """Companion web do Jarvis para celulares na mesma rede local.

    O modelo, memória e ferramentas continuam no computador. O telefone é apenas
    uma interface autenticada por PIN/token. Por padrão o servidor fica desligado.
    """

    def __init__(self, agent, config, base_dir):
        self.agent = agent
        self.config = config
        self.base_dir = Path(base_dir)
        self.host = str(config.get("mobile_companion_host", "0.0.0.0"))
        self.port = int(config.get("mobile_companion_port", 8770))
        self.web_root = Path(__file__).resolve().parent / "web"
        self.data_root = Path.home() / str(config.get("persistent_root_name", "JarvisData")) / "mobile"
        self.data_root.mkdir(parents=True, exist_ok=True)
        self.pairing_file = self.data_root / "pairing.json"
        self.upload_root = self.data_root / "uploads"
        self.upload_root.mkdir(parents=True, exist_ok=True)
        self._server = None
        self._thread = None
        self._sessions = {}
        self._sessions_lock = threading.Lock()
        self._run_lock = threading.Lock()
        self._pair_attempts = {}
        self._pin = self._load_or_create_pin()
        self._ip_cache = {"at": 0.0, "items": []}

    def _load_or_create_pin(self):
        try:
            data = json.loads(self.pairing_file.read_text(encoding="utf-8"))
            pin = str(data.get("pin", "")).strip()
            if len(pin) == 6 and pin.isdigit():
                return pin
        except Exception:
            pass
        return self.reset_pin()["pin"]

    def reset_pin(self):
        self._pin = f"{secrets.randbelow(1000000):06d}"
        self.pairing_file.write_text(
            json.dumps({"pin": self._pin, "updated_at": time.time()}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        with self._sessions_lock:
            self._sessions.clear()
        return {"ok": True, "pin": self._pin}

    def _run_hidden(self, cmd, timeout=4):
        """Run a Windows helper without flashing a console window."""
        kwargs = {
            "capture_output": True,
            "text": True,
            "timeout": timeout,
        }
        if __import__("os").name == "nt":
            try:
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            except Exception:
                pass
            try:
                si = subprocess.STARTUPINFO()
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                kwargs["startupinfo"] = si
            except Exception:
                pass
        return subprocess.run(cmd, **kwargs)

    def local_ips(self, refresh=False):
        """Return useful private IPv4 candidates, preferring real LAN interfaces."""
        now = time.time()
        cached = self._ip_cache.get("items", [])
        if cached and not refresh and now - float(self._ip_cache.get("at", 0)) < 60:
            return list(cached)

        candidates = []

        def add(value):
            try:
                ip = ipaddress.ip_address(str(value).strip())
                if ip.version != 4 or ip.is_loopback or ip.is_unspecified:
                    return
                if not (ip.is_private or ip.is_link_local):
                    return
                value = str(ip)
                if value not in candidates:
                    candidates.append(value)
            except Exception:
                pass

        if __import__("os").name == "nt":
            try:
                cmd = [
                    "powershell", "-NoProfile", "-Command",
                    "Get-NetIPAddress -AddressFamily IPv4 | "
                    "Where-Object {$_.IPAddress -notlike '127.*' -and $_.AddressState -eq 'Preferred'} | "
                    "Select-Object -ExpandProperty IPAddress"
                ]
                proc = self._run_hidden(cmd, timeout=4)
                for line in proc.stdout.splitlines():
                    add(line)
            except Exception:
                pass

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            add(s.getsockname()[0])
            s.close()
        except Exception:
            pass

        try:
            for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
                add(ip)
        except Exception:
            pass

        def priority(value):
            ip = ipaddress.ip_address(value)
            if value.startswith("192.168."):
                return (0, value)
            if value.startswith("10."):
                return (1, value)
            if value.startswith("172."):
                return (2, value)
            if ip.is_link_local:
                return (9, value)
            return (5, value)

        result = sorted(candidates, key=priority)
        self._ip_cache = {"at": now, "items": result}
        return list(result)

    def local_ip(self):
        ips = self.local_ips()
        return ips[0] if ips else "127.0.0.1"

    def url(self):
        return f"http://{self.local_ip()}:{self.port}/"

    def urls(self):
        return [f"http://{ip}:{self.port}/" for ip in self.local_ips()] or [self.url()]

    def diagnostics(self):
        running = bool(self._server and self._thread and self._thread.is_alive())
        loopback_ok = False
        if running:
            try:
                s = socket.create_connection(("127.0.0.1", self.port), timeout=1.0)
                s.close()
                loopback_ok = True
            except Exception:
                pass

        profile = ""
        firewall_rule = False
        if __import__("os").name == "nt":
            try:
                proc = self._run_hidden(
                    ["powershell","-NoProfile","-Command",
                     "(Get-NetConnectionProfile | Where-Object {$_.IPv4Connectivity -ne 'Disconnected'} | "
                     "Select-Object -First 1 -ExpandProperty NetworkCategory)"],
                    timeout=4
                )
                profile = proc.stdout.strip()
            except Exception:
                pass
            try:
                proc = self._run_hidden(
                    ["powershell","-NoProfile","-Command",
                     "if(Get-NetFirewallRule -DisplayName 'Jarvis Mobile Companion' -ErrorAction SilentlyContinue){'yes'}else{'no'}"],
                    timeout=4
                )
                firewall_rule = proc.stdout.strip().lower() == "yes"
            except Exception:
                pass

        issues = []
        if not running:
            issues.append("O Mobile Companion está desligado.")
        elif not loopback_ok:
            issues.append("O servidor mobile iniciou, mas não respondeu localmente.")
        if profile.lower() == "public":
            issues.append("A rede do Windows está marcada como Pública; a regra segura do Jarvis aceita apenas redes Privadas.")
        if running and __import__("os").name == "nt" and not firewall_rule:
            issues.append("A regra do Firewall do Windows ainda não foi criada.")
        ips = self.local_ips(refresh=True)
        if not ips:
            issues.append("Nenhum endereço IPv4 privado foi detectado.")
        if not (self.web_root / "index.html").is_file():
            issues.append(f"Interface mobile ausente em: {self.web_root}")

        return {
            "ok": not issues,
            "running": running,
            "loopback_ok": loopback_ok,
            "network_profile": profile,
            "firewall_rule": firewall_rule,
            "urls": [f"http://{ip}:{self.port}/" for ip in ips] or self.urls(),
            "web_root": str(self.web_root),
            "index_exists": (self.web_root / "index.html").is_file(),
            "issues": issues,
        }

    def status(self):
        return {
            "ok": True,
            "running": bool(self._server and self._thread and self._thread.is_alive()),
            "host": self.host,
            "port": self.port,
            "url": self.url(),
            "urls": self.urls(),
            "pin": self._pin,
            "sessions": len(self._sessions),
            "lan_only": True,
        }

    def start(self):
        if self._server and self._thread and self._thread.is_alive():
            return self.status()

        if not (self.web_root / "index.html").is_file():
            return {
                "ok": False,
                "running": False,
                "error": f"Interface mobile não encontrada em {self.web_root}",
                "web_root": str(self.web_root),
            }

        handler = self._build_handler()
        requested = int(self.config.get("mobile_companion_port", self.port))
        last_error = None
        for candidate in range(requested, requested + 11):
            try:
                self._server = ThreadingHTTPServer((self.host, candidate), handler)
                self.port = int(self._server.server_address[1])
                break
            except OSError as exc:
                last_error = exc
                self._server = None

        if not self._server:
            return {
                "ok": False,
                "running": False,
                "error": f"Não foi possível abrir as portas {requested}-{requested+10}: {last_error}",
            }

        self._server.daemon_threads = True
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="JarvisMobileCompanion",
            daemon=True
        )
        self._thread.start()
        self._ip_cache = {"at": 0.0, "items": []}
        return self.status()

    def stop(self):
        server = self._server
        self._server = None
        if server:
            try:
                server.shutdown()
                server.server_close()
            except Exception:
                pass
        self._thread = None
        with self._sessions_lock:
            self._sessions.clear()
        return self.status()

    def toggle(self):
        return self.stop() if self.status()["running"] else self.start()

    def _create_session(self):
        token = secrets.token_urlsafe(32)
        with self._sessions_lock:
            self._sessions[token] = {"created": time.time(), "last": time.time()}
        return token

    def _valid_session(self, token):
        if not token:
            return False
        with self._sessions_lock:
            session = self._sessions.get(token)
            if not session:
                return False
            if time.time() - session["last"] > 24 * 3600:
                self._sessions.pop(token, None)
                return False
            session["last"] = time.time()
        return True

    def _snapshot(self):
        project = self.agent.projects.current().get("data")
        model_status = self.agent.models.status()
        return {
            "ok": True,
            "project": project,
            "conversations": self.agent.conversations.list_sessions(limit=40),
            "current_session": self.agent.conversations.current_session_id,
            "model": {
                "fast": model_status.get("fast_model"),
                "reason": model_status.get("reasoning_model"),
                "single": model_status.get("single_model_mode"),
            },
            "hardware": self.agent.hardware.profile(),
            "mobile": {"url": self.url(), "lan_only": True},
        }

    def _history(self, session_id=None):
        sid = int(session_id or self.agent.conversations.current_session_id)
        messages = self.agent.conversations.recent_messages(limit=200, session_id=sid)
        return {"ok": True, "session_id": sid, "messages": messages}

    def _build_handler(self):
        companion = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "JarvisMobile/1.3.1"

            def log_message(self, fmt, *args):
                pass

            def _security_headers(self):
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Referrer-Policy", "no-referrer")
                self.send_header("Cache-Control", "no-store" if self.path.startswith("/api/") else "no-cache")

            def _json(self, status, payload, cookie=None):
                raw = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self._security_headers()
                if cookie:
                    self.send_header("Set-Cookie", cookie)
                self.end_headers()
                self.wfile.write(raw)

            def _body(self, max_bytes=18 * 1024 * 1024):
                n = int(self.headers.get("Content-Length", "0") or 0)
                if n > max_bytes:
                    raise ValueError("Payload grande demais.")
                raw = self.rfile.read(n) if n else b"{}"
                return json.loads(raw.decode("utf-8") or "{}")

            def _token(self):
                auth = self.headers.get("Authorization", "")
                if auth.startswith("Bearer "):
                    return auth[7:].strip()
                c = cookies.SimpleCookie(self.headers.get("Cookie", ""))
                if "jarvis_mobile" in c:
                    return c["jarvis_mobile"].value
                return ""

            def _authorized(self):
                return companion._valid_session(self._token())

            def _file(self, relative):
                target = (companion.web_root / relative.lstrip("/")).resolve()
                root = companion.web_root.resolve()
                if root not in target.parents and target != root:
                    return self._json(403, {"ok": False, "error": "Acesso negado."})
                if not target.is_file():
                    return self._json(404, {"ok": False, "error": "Arquivo não encontrado."})
                raw = target.read_bytes()
                ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                self.send_response(200)
                self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") else ""))
                self.send_header("Content-Length", str(len(raw)))
                self._security_headers()
                self.end_headers()
                self.wfile.write(raw)

            def _client_allowed(self):
                try:
                    ip = ipaddress.ip_address(self.client_address[0])
                    return ip.is_private or ip.is_loopback or ip.is_link_local
                except Exception:
                    return False

            def _pair_allowed(self):
                ip = self.client_address[0]
                now = time.time()
                attempts = [x for x in companion._pair_attempts.get(ip, []) if now - x < 60]
                companion._pair_attempts[ip] = attempts
                return len(attempts) < 6

            def do_GET(self):
                if not self._client_allowed():
                    return self._json(403, {"ok": False, "error": "Acesso permitido somente pela rede local."})
                path = urlparse(self.path).path
                if path == "/favicon.ico":
                    self.send_response(204)
                    self._security_headers()
                    self.end_headers()
                    return
                if path == "/health":
                    return self._json(200, {
                        "ok": True,
                        "service": "Jarvis Mobile Companion",
                        "port": companion.port,
                        "web_root": str(companion.web_root),
                        "index_exists": (companion.web_root / "index.html").is_file(),
                    })
                if path == "/api/status":
                    return self._json(200, {"ok": True, "name": "Jarvis", "paired": self._authorized(), "requires_pin": True})
                if path.startswith("/api/"):
                    if not self._authorized():
                        return self._json(401, {"ok": False, "error": "Não pareado."})
                    if path == "/api/snapshot":
                        return self._json(200, companion._snapshot())
                    if path == "/api/history":
                        query = urlparse(self.path).query
                        sid = None
                        for part in query.split("&"):
                            if part.startswith("session="):
                                try:
                                    sid = int(part.split("=", 1)[1])
                                except Exception:
                                    pass
                        return self._json(200, companion._history(sid))
                    return self._json(404, {"ok": False, "error": "Rota não encontrada."})

                if path == "/":
                    index_file = companion.web_root / "index.html"
                    if index_file.is_file():
                        return self._file("index.html")
                    raw = (
                        "<!doctype html><meta charset='utf-8'><title>Jarvis Mobile</title>"
                        "<body style='font-family:Segoe UI;background:#07090f;color:#fff;padding:32px'>"
                        "<h1>Jarvis Mobile não encontrou a interface web.</h1>"
                        f"<p>Diretório esperado: <code>{companion.web_root}</code></p>"
                        "<p>Atualize/reinstale o Jarvis e tente novamente.</p></body>"
                    ).encode("utf-8")
                    self.send_response(500)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(raw)))
                    self._security_headers()
                    self.end_headers()
                    self.wfile.write(raw)
                    return
                return self._file(path)

            def do_POST(self):
                if not self._client_allowed():
                    return self._json(403, {"ok": False, "error": "Acesso permitido somente pela rede local."})
                path = urlparse(self.path).path
                try:
                    body = self._body()
                except Exception as exc:
                    return self._json(400, {"ok": False, "error": str(exc)})

                if path == "/api/pair":
                    if not self._pair_allowed():
                        return self._json(429, {"ok": False, "error": "Muitas tentativas. Aguarde um minuto."})
                    pin = str(body.get("pin", "")).strip()
                    if not secrets.compare_digest(pin, companion._pin):
                        companion._pair_attempts.setdefault(self.client_address[0], []).append(time.time())
                        return self._json(401, {"ok": False, "error": "PIN inválido."})
                    companion._pair_attempts.pop(self.client_address[0], None)
                    token = companion._create_session()
                    cookie = f"jarvis_mobile={token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=86400"
                    return self._json(200, {"ok": True, "token": token}, cookie=cookie)

                if not self._authorized():
                    return self._json(401, {"ok": False, "error": "Não pareado."})

                if path == "/api/chat":
                    message = str(body.get("message", "")).strip()
                    if not message:
                        return self._json(400, {"ok": False, "error": "Mensagem vazia."})
                    if not companion._run_lock.acquire(blocking=False):
                        return self._json(409, {"ok": False, "error": "Jarvis já está processando outra solicitação."})
                    try:
                        states = []
                        answer = companion.agent.run(message, status=lambda s: states.append(str(s)))
                        return self._json(200, {
                            "ok": True,
                            "answer": str(answer),
                            "metadata": companion.agent._last_response_metadata or {},
                            "status": states[-1] if states else "completed",
                        })
                    except Exception as exc:
                        return self._json(500, {"ok": False, "error": str(exc)})
                    finally:
                        companion._run_lock.release()

                if path == "/api/conversation/new":
                    result = companion.agent.new_conversation()
                    return self._json(200, result if isinstance(result, dict) else {"ok": True})

                if path == "/api/conversation/select":
                    try:
                        sid = int(body.get("session_id"))
                    except Exception:
                        return self._json(400, {"ok": False, "error": "session_id inválido."})
                    result = companion.agent.conversations.set_current(sid)
                    return self._json(200 if result.get("ok") else 404, result)

                if path == "/api/upload":
                    name = Path(str(body.get("name", "arquivo"))).name
                    encoded = str(body.get("data", ""))
                    if not encoded:
                        return self._json(400, {"ok": False, "error": "Arquivo vazio."})
                    try:
                        raw = base64.b64decode(encoded, validate=True)
                    except Exception:
                        return self._json(400, {"ok": False, "error": "Conteúdo inválido."})
                    if len(raw) > 15 * 1024 * 1024:
                        return self._json(413, {"ok": False, "error": "Limite mobile: 15 MB por arquivo."})
                    dest = companion.upload_root / f"{int(time.time())}_{name}"
                    dest.write_bytes(raw)
                    result = companion.agent.attachments.add_files(
                        [str(dest)],
                        session_id=companion.agent.conversations.current_session_id,
                        project_id=companion.agent.projects.current_id(),
                    )
                    return self._json(200 if result.get("ok") else 400, result)

                return self._json(404, {"ok": False, "error": "Rota não encontrada."})

        return Handler
