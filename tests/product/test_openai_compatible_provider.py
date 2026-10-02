import json
import threading
from http.server import BaseHTTPRequestHandler,HTTPServer

from jarvis.models import OpenAICompatibleProvider,ChatMessage


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        body=json.dumps({"data":[{"id":"test-model"}]}).encode()
        self.send_response(200);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def do_POST(self):
        body=json.dumps({
            "choices":[{"message":{"content":"resposta"},"finish_reason":"stop"}],
            "usage":{"total_tokens":3},
        }).encode()
        self.send_response(200);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)


def test_openai_compatible_provider():
    server=HTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        base=f"http://127.0.0.1:{server.server_address[1]}"
        p=OpenAICompatibleProvider("cloud",base,"token","test-model")
        assert p.health()["status"]=="healthy"
        result=p.chat([ChatMessage("user","oi")])
        assert result.content=="resposta"
    finally:
        server.shutdown();server.server_close()
