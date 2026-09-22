import json
import tempfile
import urllib.request
from pathlib import Path

from mobile.companion import MobileCompanion


class FakeProjects:
    def current(self): return {"data": {"id": 1, "name": "Projeto teste", "description": "mobile"}}
    def current_id(self): return 1

class FakeConversations:
    current_session_id = 7
    def list_sessions(self, limit=40): return {"ok": True, "items": [{"id": 7, "title": "Teste"}], "current": 7}
    def recent_messages(self, limit=200, session_id=None): return [{"role": "user", "content": "oi", "metadata": {}}]
    def set_current(self, sid): self.current_session_id = sid; return {"ok": True, "session_id": sid}

class FakeModels:
    def status(self): return {"fast_model": "qwen3:1.7b", "reasoning_model": "qwen3:4b", "single_model_mode": False}

class FakeHardware:
    def profile(self): return {"tier": "standard", "ram_gb": 16, "cpu_threads": 12}

class FakeAttachments:
    def add_files(self, *args, **kwargs): return {"ok": True, "items": [], "count": 0}

class FakeAgent:
    def __init__(self):
        self.projects=FakeProjects(); self.conversations=FakeConversations(); self.models=FakeModels(); self.hardware=FakeHardware(); self.attachments=FakeAttachments(); self._last_response_metadata={"model":"qwen3:1.7b"}
    def run(self, message, status=None):
        if status: status("Conversando")
        return f"eco: {message}"
    def new_conversation(self): return {"ok": True, "session_id": 8}


def request(url, method="GET", payload=None, token=None):
    data=None; headers={}
    if payload is not None:
        data=json.dumps(payload).encode("utf-8"); headers["Content-Type"]="application/json"
    if token: headers["Authorization"]="Bearer "+token
    req=urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=5) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def main():
    with tempfile.TemporaryDirectory() as td:
        base=Path(__file__).resolve().parent
        cfg={"mobile_companion_host":"127.0.0.1","mobile_companion_port":0,"persistent_root_name":"JarvisData"}
        comp=MobileCompanion(FakeAgent(),cfg,base)
        # redirect persistent test data into temp
        comp.data_root=Path(td); comp.pairing_file=Path(td)/"pairing.json"; comp.upload_root=Path(td)/"uploads"; comp.upload_root.mkdir(); comp.reset_pin()
        state=comp.start(); assert state["running"] and state["port"]>0
        base_url=f"http://127.0.0.1:{state['port']}"
        status,d=request(base_url+"/api/status"); assert status==200 and d["requires_pin"]
        status,d=request(base_url+"/api/pair","POST",{"pin":state["pin"]}); assert d["ok"]; token=d["token"]
        status,d=request(base_url+"/api/snapshot",token=token); assert d["ok"] and d["project"]["name"]=="Projeto teste"
        status,d=request(base_url+"/api/chat","POST",{"message":"teste"},token); assert d["answer"]=="eco: teste"
        comp.stop(); assert not comp.status()["running"]
        print("[OK] Mobile Companion: pairing, snapshot e chat local.")

if __name__=="__main__": main()
