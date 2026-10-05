from __future__ import annotations

from dataclasses import dataclass
import json
import subprocess
import threading
import queue


@dataclass(slots=True)
class MCPServer:
    server_id:str
    command:list[str]
    enabled:bool=True
    env:dict|None=None


class MCPError(RuntimeError):
    pass


class MCPStdioClient:
    """Minimal MCP stdio JSON-RPC client.

    The transport is isolated behind this adapter so a future official MCP SDK
    can replace it without changing Jarvis agents/tools.
    """

    def __init__(self,server:MCPServer):
        self.server=server
        self.process=None
        self._counter=0
        self._responses=queue.Queue()
        self._reader=None

    def start(self):
        if self.process and self.process.poll() is None:
            return
        if not self.server.enabled:
            raise MCPError(f'MCP server desabilitado: {self.server.server_id}')
        self.process=subprocess.Popen(
            self.server.command,
            stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,bufsize=1,env=self.server.env,
        )
        self._reader=threading.Thread(target=self._read_loop,daemon=True)
        self._reader.start()

    def _read_loop(self):
        assert self.process and self.process.stdout
        for line in self.process.stdout:
            line=line.strip()
            if not line:
                continue
            try:self._responses.put(json.loads(line))
            except Exception:continue

    def _rpc(self,method,params=None,timeout=20):
        self.start()
        self._counter+=1
        rid=self._counter
        payload={'jsonrpc':'2.0','id':rid,'method':method}
        if params is not None: payload['params']=params
        assert self.process and self.process.stdin
        self.process.stdin.write(json.dumps(payload,separators=(',',':'))+'\n')
        self.process.stdin.flush()
        while True:
            try:message=self._responses.get(timeout=timeout)
            except queue.Empty as exc:raise MCPError(f'Timeout MCP em {method}') from exc
            if message.get('id')==rid:
                if message.get('error'):
                    raise MCPError(str(message['error']))
                return message.get('result')

    def initialize(self):
        return self._rpc('initialize',{
            'protocolVersion':'2025-06-18',
            'capabilities':{},
            'clientInfo':{'name':'Jarvis Next','version':'1.0.0rc3'},
        })

    def list_tools(self):
        return self._rpc('tools/list',{}) or {}

    def call_tool(self,name,arguments=None):
        return self._rpc('tools/call',{
            'name':name,'arguments':arguments or {}
        })

    def health(self):
        if not self.server.enabled:return {'status':'disabled'}
        try:
            self.start()
            return {
                'status':'healthy' if self.process.poll() is None else 'error',
                'server_id':self.server.server_id,
                'pid':self.process.pid if self.process else None,
            }
        except Exception as exc:
            return {'status':'error','error':str(exc)}

    def close(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:self.process.kill()
        self.process=None


class MCPRegistry:
    def __init__(self):
        self._clients={}

    def register(self,server):
        self._clients[server.server_id]=MCPStdioClient(server)

    def client(self,server_id):
        return self._clients[server_id]

    def health(self):
        return {key:value.health() for key,value in self._clients.items()}

    def close(self):
        for client in self._clients.values():
            client.close()
