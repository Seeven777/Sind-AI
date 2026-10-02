from __future__ import annotations

from dataclasses import dataclass
import json
import urllib.request


@dataclass(slots=True)
class RemoteAgent:
    agent_id:str
    endpoint:str
    enabled:bool=True
    token:str|None=None


class RemoteAgentClient:
    def __init__(self,agent:RemoteAgent,timeout=30):
        self.agent=agent
        self.timeout=timeout

    def _request(self,path,payload=None):
        url=self.agent.endpoint.rstrip('/')+'/'+path.lstrip('/')
        data=json.dumps(payload).encode('utf-8') if payload is not None else None
        headers={'Accept':'application/json'}
        if data is not None:headers['Content-Type']='application/json'
        if self.agent.token:headers['Authorization']=f'Bearer {self.agent.token}'
        req=urllib.request.Request(url,data=data,headers=headers)
        with urllib.request.urlopen(req,timeout=self.timeout) as response:
            return json.loads(response.read().decode('utf-8'))

    def health(self):
        if not self.agent.enabled:return {'status':'disabled'}
        try:
            return {'status':'healthy','response':self._request('/health')}
        except Exception as exc:
            return {'status':'unavailable','error':str(exc)}

    def submit(self,objective,artifacts=None,metadata=None):
        if not self.agent.enabled:
            raise RuntimeError('Remote agent disabled.')
        return self._request('/tasks',{
            'objective':objective,
            'artifacts':artifacts or [],
            'metadata':metadata or {},
        })


class A2ARegistry:
    def __init__(self):
        self._clients={}

    def register(self,agent):
        self._clients[agent.agent_id]=RemoteAgentClient(agent)

    def health(self):
        return {key:client.health() for key,client in self._clients.items()}
