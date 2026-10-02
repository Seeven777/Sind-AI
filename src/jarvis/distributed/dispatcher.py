from __future__ import annotations

import json
import urllib.request


class DistributedDispatcher:
    def __init__(self,node_registry,timeout=120):
        self.node_registry=node_registry
        self.timeout=timeout

    def dispatch(self,capability,objective,*,metadata=None,token=None):
        node=self.node_registry.choose(capability)
        if not node:
            return {
                'status':'no_node',
                'capability':capability,
                'objective':objective,
            }
        if node['node_id']=='local' or not node.get('endpoint'):
            return {
                'status':'local',
                'node':node,
                'objective':objective,
            }
        url=node['endpoint'].rstrip('/')+'/tasks'
        payload=json.dumps({
            'objective':objective,
            'capability':capability,
            'metadata':metadata or {},
        }).encode('utf-8')
        headers={'Content-Type':'application/json','Accept':'application/json'}
        if token:headers['Authorization']=f'Bearer {token}'
        req=urllib.request.Request(url,data=payload,headers=headers)
        try:
            with urllib.request.urlopen(req,timeout=self.timeout) as response:
                result=json.loads(response.read().decode('utf-8'))
            return {'status':'submitted','node':node,'result':result}
        except Exception as exc:
            return {'status':'failed','node':node,'error':str(exc)}
