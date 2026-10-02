import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from jarvis.models import ChatMessage, OllamaProvider


class Handler(BaseHTTPRequestHandler):
    attempts = 0

    def log_message(self, *args):
        return

    def do_GET(self):
        if self.path == "/api/tags":
            body = json.dumps({"models": [{"name": "qwen3.5:4b"}]}).encode()
            self.send_response(200); self.send_header("Content-Type","application/json")
            self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body); return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/show":
            body = json.dumps({"thinking":{"values":[True,False],"default":True}}).encode()
        elif self.path == "/api/chat":
            Handler.attempts += 1
            assert payload.get("think") is False
            if Handler.attempts == 1:
                body = json.dumps({
                    "model":"qwen3.5:4b",
                    "message":{"role":"assistant","content":"","thinking":"raciocínio interno"},
                    "done_reason":"stop",
                    "eval_count":1024,
                }).encode()
            else:
                body = json.dumps({
                    "model":"qwen3.5:4b",
                    "message":{"role":"assistant","content":"resposta recuperada","thinking":""},
                    "done_reason":"stop",
                    "eval_count":12,
                }).encode()
        else:
            self.send_error(404); return
        self.send_response(200); self.send_header("Content-Type","application/json")
        self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)


def test_empty_content_is_retried_without_exposing_thinking():
    Handler.attempts = 0
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        provider = OllamaProvider(f"http://127.0.0.1:{server.server_port}", "qwen3.5:4b", timeout_seconds=2)
        response = provider.chat([ChatMessage("user", "teste")])
        assert response.content == "resposta recuperada"
        assert "raciocínio interno" not in response.content
        assert response.metadata["retried_for_empty_content"] is True
        assert Handler.attempts == 2
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=2)
