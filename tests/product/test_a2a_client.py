import json
import threading
from http.server import BaseHTTPRequestHandler,HTTPServer

from jarvis.a2a import RemoteAgent,RemoteAgentClient


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_GET(self):
        body=json.dumps({"ok":True}).encode()
        self.send_response(200);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def do_POST(self):
        n=int(self.headers.get("Content-Length","0"))
        payload=json.loads(self.rfile.read(n) or b"{}")
        body=json.dumps({"accepted":True,"objective":payload.get("objective")}).encode()
        self.send_response(200);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)


def test_remote_agent_client():
    server=HTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        endpoint=f"http://127.0.0.1:{server.server_address[1]}"
        client=RemoteAgentClient(RemoteAgent("x",endpoint))
        assert client.health()["status"]=="healthy"
        assert client.submit("teste")["accepted"] is True
    finally:
        server.shutdown();server.server_close()
