from __future__ import annotations

import asyncio
import json
import mimetypes
import threading
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from jarvis.app.product_runtime import start_product_runtime


class _State:
    def __init__(self, runtime, loop):
        self.runtime = runtime
        self.loop = loop

    def call(self, coro, timeout=900):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        return future.result(timeout=timeout)


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

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/api/ping":
                return self._send(200, {
                    "ok": True,
                    "service": "jarvis-ui",
                    "run_id": state.runtime.foundation.run_id,
                })
            if path == "/api/hq":
                return self._send(200, state.runtime.hq.snapshot())
            if path == "/api/briefing":
                return self._send(200, state.runtime.briefing.snapshot())
            if path == "/api/health":
                return self._send(200, {
                    "foundation": state.runtime.foundation.health.snapshot(),
                    "privacy": {"mode": state.runtime.foundation.config.privacy.mode},
                    "models": state.runtime.model_registry.health(),
                    "connectors": state.runtime.connectors.health(),
                })
            if path == "/api/connectors":
                return self._send(200, {
                    "health": state.runtime.connectors.health(),
                    "sources": state.runtime.connector_repository.sources(),
                    "counts": state.runtime.connector_repository.counts(),
                })
            if path == "/api/watchers":
                return self._send(200, state.runtime.watcher_repository.enabled())
            if path == "/api/system":
                return self._send(200, {
                    "foundation": state.runtime.foundation.health.snapshot(),
                    "models": state.runtime.model_registry.health(),
                    "connectors": state.runtime.connectors.health(),
                    "browser": state.runtime.browser.health(),
                    "windows": state.runtime.windows.health(),
                    "voice": state.runtime.voice.health(),
                    "mcp": state.runtime.mcp.health(),
                    "a2a": state.runtime.a2a.health(),
                    "nodes": state.runtime.nodes.repository.list(),
                    "skills": state.runtime.skill_manager.repository.list(),
                    "capabilities": state.runtime.capabilities.inventory(),
                    "scheduler": state.runtime.scheduler_repository.all(),
                    "watchers": state.runtime.watcher_repository.enabled(),
                    "google": state.runtime.google_oauth.status(),
                })
            if path == "/api/projects":
                return self._send(200, state.runtime.projects.list())
            if path == "/api/skills":
                return self._send(200, state.runtime.skill_manager.repository.list())
            if path == "/api/capabilities":
                return self._send(200, state.runtime.capabilities.inventory())
            if path == "/api/opportunities":
                return self._send(200, state.runtime.opportunities.scan())
            if path == "/api/tool-runs":
                return self._send(200, state.runtime.tool_runs.recent(50))
            if path == "/api/memory":
                return self._send(200, state.runtime.memory.repository.recent(100))
            if path == "/api/agents":
                return self._send(200, state.runtime.hq.agent_directory())
            if path == "/api/agency":
                return self._send(200, {
                    "status": state.runtime.agency_catalog.status(),
                    "router": state.runtime.agent_router.status(),
                    "runbooks": [
                        {
                            "slug": x.get("slug"), "title": x.get("title"),
                            "mode": x.get("mode"), "duration": x.get("duration"),
                            "summary": x.get("summary"),
                        } for x in state.runtime.agency_catalog.runbooks()
                    ],
                })
            if path == "/api/google/status":
                return self._send(200, state.runtime.google_oauth.status())
            if path == "/":
                target = assets / "companion.html"
            elif path == "/hq":
                target = assets / "index.html"
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
            path = urlparse(self.path).path
            try:
                payload = self._json_body()
                if path == "/api/chat":
                    cid = payload.get("conversation_id")
                    if not cid:
                        cid = state.runtime.chat.new_conversation()
                    text = str(payload.get("text") or "").strip()
                    if not text:
                        return self._send(400, {"error": "text obrigatório"})
                    result = state.call(state.runtime.chat.send(cid, text))
                    result["conversation_id"] = cid
                    return self._send(200, result)
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
                    operator = state.runtime.agent_registry.runtime("operations.operator")
                    result = state.call(operator.resume_approval(approval_id))
                    return self._send(200, result)
                if path.startswith("/api/approval/") and path.endswith("/reject"):
                    approval_id = path.split("/")[3]
                    operator = state.runtime.agent_registry.runtime("operations.operator")
                    result = state.call(operator.reject_approval(approval_id))
                    return self._send(200, result)
                if path == "/api/connectors/sync":
                    result = state.call(state.runtime.connectors.sync_all())
                    state.call(state.runtime.watchers.check_all())
                    return self._send(200, result)
                if path == "/api/scheduler/tick":
                    result = state.call(state.runtime.scheduler.run_due())
                    return self._send(200, result)
                if path == "/api/project":
                    name = str(payload.get("name") or "").strip()
                    if not name:
                        return self._send(400, {"error": "name obrigatório"})
                    result = state.runtime.projects.create(
                        name,
                        str(payload.get("objective") or ""),
                        state.runtime.workspace.get("workspace_id"),
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
                    state.runtime.google_oauth.token_store.delete()
                    return self._send(200, {"status": "disconnected"})
                if path == "/api/skill/scaffold":
                    skill_id = str(payload.get("skill_id") or "").strip()
                    if not skill_id:
                        return self._send(400, {"error": "skill_id obrigatório"})
                    result = state.runtime.skill_manager.create_scaffold(
                        skill_id,
                        str(payload.get("description") or "Skill Jarvis"),
                        tuple(payload.get("capabilities") or ()),
                    )
                    return self._send(200, result)
                return self._send(404, {"error": "not found"})
            except Exception as exc:
                return self._send(500, {"error": str(exc)})

    return Handler


async def serve_hq(
    data_dir=None,
    *,
    host="127.0.0.1",
    port=4760,
    open_browser=True,
    start_page="/",
):
    url = f"http://{host}:{port}{start_page}"

    # A second launcher must reuse the existing Jarvis process instead of
    # creating a competing ProductRuntime and tripping the single-instance lock.
    if ui_server_alive(host, port):
        print(f"Jarvis já está ativo. Reutilizando: {url}")
        if open_browser:
            webbrowser.open(url)
        return

    runtime = await start_product_runtime(data_dir)
    loop = asyncio.get_running_loop()
    state = _State(runtime, loop)

    async def background_services():
        while True:
            try:
                await runtime.scheduler.run_due()
            except Exception:
                pass
            await asyncio.sleep(30)

    background_task = asyncio.create_task(
        background_services(),
        name="jarvis-background-services",
    )
    server = ThreadingHTTPServer((host, port), _handler(state))
    thread = threading.Thread(
        target=server.serve_forever,
        name="jarvis-local-ui",
        daemon=True,
    )
    thread.start()
    print(f"Jarvis local UI: {url}")
    print(f"Companion: http://{host}:{port}/")
    print(f"HQ:        http://{host}:{port}/hq")
    print(f"Missões:   http://{host}:{port}/mission-control")
    print(f"Projetos:  http://{host}:{port}/projects")
    print(f"Agentes:   http://{host}:{port}/agents")
    print(f"Memória:   http://{host}:{port}/memory")
    print(f"Sistema:   http://{host}:{port}/system")
    print("Ctrl+C para fechar.")
    if open_browser:
        webbrowser.open(url)
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
