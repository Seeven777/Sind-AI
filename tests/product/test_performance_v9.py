import asyncio
import json
import queue
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import ChatMessage, MockModelProvider, OllamaProvider
from jarvis.performance import PerformanceMonitor


def test_performance_monitor_tracks_latency_window():
    monitor = PerformanceMonitor(max_samples=20)
    monitor.record(kind='chat_stream', total_ms=900, ttft_ms=120, model='fast')
    monitor.record(kind='chat_stream', total_ms=1100, ttft_ms=160, model='fast')
    snap = monitor.snapshot()
    assert snap['chat']['samples'] == 2
    assert snap['chat']['median_total_ms'] == 1000
    assert snap['chat']['median_ttft_ms'] == 140


def test_chat_stream_pipeline_emits_delta_and_metric(tmp_path: Path):
    async def scenario():
        rt = await start_product_runtime(tmp_path / 'data', model_provider=MockModelProvider('resposta em fluxo'))
        try:
            cid = rt.chat.new_conversation()
            out = queue.Queue()
            result = await rt.chat.send_stream_to_queue(cid, 'Olá Jarvis', out, mode='fast')
            events=[]
            while not out.empty():
                events.append(out.get_nowait())
            assert ''.join(x.get('text','') for x in events if x.get('type')=='delta') == 'resposta em fluxo'
            assert any(x.get('type')=='done' for x in events)
            assert result['performance']['ttft_ms'] >= 0
            assert rt.performance.snapshot()['chat']['samples'] == 1
        finally:
            await rt.close()
    asyncio.run(scenario())


class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        return

    def do_POST(self):
        length=int(self.headers.get('Content-Length','0'))
        payload=json.loads(self.rfile.read(length) or b'{}')
        if self.path == '/api/show':
            body=json.dumps({'thinking':{'values':[True,False],'default':True}}).encode()
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
        if self.path == '/api/chat':
            assert payload['stream'] is True
            assert payload['keep_alive'] == '30m'
            assert payload['think'] is False
            rows=[
                {'model':'qwen3.5:4b','message':{'content':'Olá '},'done':False},
                {'model':'qwen3.5:4b','message':{'content':'senhor.'},'done':True,'done_reason':'stop','eval_count':2},
            ]
            body=('\n'.join(json.dumps(x) for x in rows)+'\n').encode()
            self.send_response(200);self.send_header('Content-Type','application/x-ndjson');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
        self.send_error(404)


def test_ollama_stream_delivers_incremental_answer():
    server=HTTPServer(('127.0.0.1',0),StreamHandler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        provider=OllamaProvider(f'http://127.0.0.1:{server.server_port}','qwen3.5:4b',timeout_seconds=2)
        chunks=[]
        response=provider.chat_stream([ChatMessage('user','teste')],on_chunk=chunks.append)
        assert chunks == ['Olá ','senhor.']
        assert response.content == 'Olá senhor.'
        assert response.metadata['streamed'] is True
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)


def test_hq_stream_endpoint_returns_ndjson_without_waiting_for_json_envelope(tmp_path: Path):
    import urllib.request
    from jarvis.hq.server import _State, _handler
    from http.server import ThreadingHTTPServer

    loop=asyncio.new_event_loop()
    ready=threading.Event()
    def run_loop():
        asyncio.set_event_loop(loop);ready.set();loop.run_forever()
    loop_thread=threading.Thread(target=run_loop,daemon=True);loop_thread.start();assert ready.wait(2)
    rt=asyncio.run_coroutine_threadsafe(
        start_product_runtime(tmp_path/'http-data',model_provider=MockModelProvider('stream HTTP ok')),loop
    ).result(5)
    state=_State(rt,loop)
    server=ThreadingHTTPServer(('127.0.0.1',0),_handler(state))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        host,port=server.server_address
        cid=state.call_sync(rt.chat.new_conversation)
        body=json.dumps({'conversation_id':cid,'text':'Olá','mode':'fast','attachments':[]}).encode()
        req=urllib.request.Request(f'http://{host}:{port}/api/chat/stream',data=body,headers={'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=5) as response:
            events=[json.loads(line.decode()) for line in response if line.strip()]
        assert response.headers.get_content_type() == 'application/x-ndjson'
        assert any(x.get('type')=='delta' and 'stream HTTP ok' in x.get('text','') for x in events)
        assert any(x.get('type')=='done' for x in events)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)
        asyncio.run_coroutine_threadsafe(rt.close(),loop).result(5)
        loop.call_soon_threadsafe(loop.stop);loop_thread.join(timeout=2);loop.close()
