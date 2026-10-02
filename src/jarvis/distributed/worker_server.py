from __future__ import annotations

import asyncio
import json
import os
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlparse

from jarvis.app.product_runtime import start_product_runtime


class _State:
    def __init__(self,runtime,loop,token):
        self.runtime=runtime;self.loop=loop;self.token=token

    def call(self,coro,timeout=1200):
        return asyncio.run_coroutine_threadsafe(coro,self.loop).result(timeout=timeout)


def _handler(state):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):return

        def _send(self,status,payload):
            body=json.dumps(payload,ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(body)))
            self.end_headers();self.wfile.write(body)

        def _authorized(self):
            if not state.token:return True
            return self.headers.get('Authorization')==f'Bearer {state.token}'

        def do_GET(self):
            if urlparse(self.path).path!='/health':
                return self._send(404,{'error':'not found'})
            return self._send(200,{
                'ok':True,
                'service':'jarvis-worker',
                'run_id':state.runtime.foundation.run_id,
                'agents':[c.agent_id for c in state.runtime.agent_registry.available()],
                'tools':list(state.runtime.tool_registry.list_ids()),
            })

        def do_POST(self):
            if not self._authorized():
                return self._send(401,{'error':'unauthorized'})
            if urlparse(self.path).path!='/tasks':
                return self._send(404,{'error':'not found'})
            try:
                n=int(self.headers.get('Content-Length','0'))
                payload=json.loads(self.rfile.read(n) or b'{}')
                objective=str(payload.get('objective') or '').strip()
                if not objective:return self._send(400,{'error':'objective obrigatório'})
                mode=(payload.get('metadata') or {}).get('mode')
                if mode=='team':
                    result=state.call(state.runtime.missions.run(
                        objective,title='Remote mission'
                    ))
                else:
                    result=state.call(state.runtime.orchestrator.handle(objective))
                return self._send(200,result)
            except Exception as exc:
                return self._send(500,{'error':str(exc)})
    return Handler


async def serve_worker(data_dir=None,host='127.0.0.1',port=4770):
    runtime=await start_product_runtime(data_dir)
    loop=asyncio.get_running_loop()
    token=os.environ.get('JARVIS_WORKER_TOKEN')
    if host not in {'127.0.0.1','localhost','::1'} and not token:
        await runtime.close()
        raise RuntimeError(
            'JARVIS_WORKER_TOKEN é obrigatório ao expor worker fora de localhost.'
        )
    state=_State(runtime,loop,token)
    server=ThreadingHTTPServer((host,port),_handler(state))
    thread=threading.Thread(target=server.serve_forever,daemon=True)
    thread.start()
    print(f'Jarvis Worker: http://{host}:{port}')
    try:
        while True:await asyncio.sleep(1)
    finally:
        server.shutdown();server.server_close();await runtime.close()
