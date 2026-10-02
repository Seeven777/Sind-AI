import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from jarvis.models import ChatMessage, OllamaProvider


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def do_GET(self):
        if self.path == "/api/tags":
            body = json.dumps({"models": [{"name": "qwen3.5:4b"}]}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/api/show":
            body = json.dumps({
                "capabilities": ["completion", "thinking"],
                "thinking": {"values": [True, False], "default": True},
            }).encode()
        elif self.path == "/api/chat":
            assert payload["model"] == "qwen3.5:4b"
            assert payload["stream"] is False
            assert payload["messages"][-1]["content"] == "teste"
            assert payload["think"] is False
            body = json.dumps({
                "model": "qwen3.5:4b",
                "message": {"role": "assistant", "content": "resposta local"},
                "done_reason": "stop",
            }).encode()
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_ollama_http_contract():
    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        provider = OllamaProvider(
            f"http://127.0.0.1:{server.server_port}", "qwen3.5:4b", timeout_seconds=2
        )
        health = provider.health()
        assert health["default_model_present"] is True
        assert health["thinking"]["default"] is True
        response = provider.chat([ChatMessage("user", "teste")])
        assert response.content == "resposta local"
        assert response.model == "qwen3.5:4b"
        assert response.metadata["think_disabled"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
