import asyncio
import json
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from types import SimpleNamespace

from jarvis.hq.server import _State, _handler


def test_hq_handler_marshals_runtime_calls_to_owner_loop_thread():
    loop = asyncio.new_event_loop()
    ready = threading.Event()
    owner_thread_id = {"value": None}

    def run_loop():
        asyncio.set_event_loop(loop)
        owner_thread_id["value"] = threading.get_ident()
        ready.set()
        loop.run_forever()

    loop_thread = threading.Thread(target=run_loop, daemon=True)
    loop_thread.start()
    assert ready.wait(2)

    class HQ:
        def snapshot(self):
            assert threading.get_ident() == owner_thread_id["value"]
            return {"thread_affinity": "ok"}

    runtime = SimpleNamespace(hq=HQ())
    state = _State(runtime, loop)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _handler(state))
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        host, port = server.server_address
        with urllib.request.urlopen(f"http://{host}:{port}/api/hq", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload == {"thread_affinity": "ok"}
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=2)
        loop.call_soon_threadsafe(loop.stop)
        loop_thread.join(timeout=2)
        loop.close()
