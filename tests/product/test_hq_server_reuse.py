import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from jarvis.hq.server import ui_server_alive


class _Ping(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        if self.path != "/api/ping":
            self.send_response(404); self.end_headers(); return
        body = json.dumps({"ok": True, "service": "jarvis-ui"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def test_ui_server_alive_detects_existing_server():
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Ping)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        assert ui_server_alive("127.0.0.1", server.server_port, timeout=1.0)
    finally:
        server.shutdown(); server.server_close()
