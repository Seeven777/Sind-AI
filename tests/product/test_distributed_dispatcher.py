import json
import threading
from http.server import BaseHTTPRequestHandler,HTTPServer

from jarvis.distributed import NodeRepository,NodeRegistry,DistributedDispatcher
from jarvis.storage import Database,MigrationEngine
from pathlib import Path


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def do_POST(self):
        n=int(self.headers.get("Content-Length","0"))
        payload=json.loads(self.rfile.read(n) or b"{}")
        body=json.dumps({"accepted":True,"objective":payload["objective"]}).encode()
        self.send_response(200);self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)


def test_dispatch_to_remote_node(tmp_path:Path):
    db=Database(tmp_path/"x.db");conn=db.open()
    MigrationEngine(conn,Path(__file__).resolve().parents[2]/"migrations").apply_pending()
    repo=NodeRepository(conn);registry=NodeRegistry(repo)
    server=HTTPServer(("127.0.0.1",0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        endpoint=f"http://127.0.0.1:{server.server_address[1]}"
        registry.register_remote("n1","Node 1",endpoint,("coding",))
        result=DistributedDispatcher(registry).dispatch("coding","teste")
        assert result["status"]=="submitted"
        assert result["result"]["accepted"] is True
    finally:
        server.shutdown();server.server_close();db.close()
