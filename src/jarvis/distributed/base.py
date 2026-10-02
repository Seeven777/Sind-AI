from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime,timezone
import json


def now():
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True,frozen=True)
class NodeCard:
    node_id:str
    name:str
    capabilities:tuple[str,...]
    endpoint:str|None=None
    status:str='offline'


class NodeRepository:
    def __init__(self,conn):self.conn=conn

    def upsert(self,node:NodeCard,metadata=None):
        ts=now()
        self.conn.execute(
            """INSERT INTO worker_nodes(
               node_id,name,endpoint,status,capabilities_json,metadata_json,last_seen_at,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?)
               ON CONFLICT(node_id) DO UPDATE SET
                 name=excluded.name,endpoint=excluded.endpoint,status=excluded.status,
                 capabilities_json=excluded.capabilities_json,metadata_json=excluded.metadata_json,
                 last_seen_at=excluded.last_seen_at,updated_at=excluded.updated_at""",
            (
                node.node_id,node.name,node.endpoint,node.status,
                json.dumps(list(node.capabilities)),
                json.dumps(metadata or {},ensure_ascii=False),
                ts,ts,ts
            )
        );self.conn.commit()

    def list(self):
        rows=self.conn.execute('SELECT * FROM worker_nodes ORDER BY name').fetchall()
        result=[]
        for row in rows:
            item=dict(row)
            item['capabilities']=json.loads(item.pop('capabilities_json') or '[]')
            item['metadata']=json.loads(item.pop('metadata_json') or '{}')
            result.append(item)
        return result


class NodeRegistry:
    def __init__(self,repository:NodeRepository):
        self.repository=repository

    def register_local(self,name='PC principal',capabilities=()):
        node=NodeCard('local',name,tuple(capabilities),None,'online')
        self.repository.upsert(node,{'kind':'local'})
        return node

    def register_remote(self,node_id,name,endpoint,capabilities):
        node=NodeCard(node_id,name,tuple(capabilities),endpoint,'configured')
        self.repository.upsert(node,{'kind':'remote'})
        return node

    def choose(self,capability):
        nodes=self.repository.list()
        candidates=[x for x in nodes if capability in x['capabilities'] and x['status'] in {'online','healthy','configured'}]
        return candidates[0] if candidates else None
