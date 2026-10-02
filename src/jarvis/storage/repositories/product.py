from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


class ConversationRepository:
    def __init__(self, conn): self.conn = conn
    def create(self, title='Nova conversa'):
        cid=str(uuid4()); ts=now()
        self.conn.execute(
            'INSERT INTO conversations(conversation_id,title,created_at,updated_at) VALUES(?,?,?,?)',
            (cid,title,ts,ts)
        ); self.conn.commit(); return cid
    def add_message(self,cid,role,content,metadata=None):
        mid=str(uuid4()); ts=now()
        self.conn.execute(
            'INSERT INTO messages(message_id,conversation_id,role,content,created_at,metadata_json) VALUES(?,?,?,?,?,?)',
            (mid,cid,role,content,ts,json.dumps(metadata or {},ensure_ascii=False))
        )
        self.conn.execute('UPDATE conversations SET updated_at=? WHERE conversation_id=?',(ts,cid))
        self.conn.commit(); return mid
    def recent_messages(self,cid,limit=20):
        rows=self.conn.execute(
            'SELECT role,content,created_at,metadata_json FROM messages WHERE conversation_id=? ORDER BY created_at DESC LIMIT ?',
            (cid,limit)
        ).fetchall()
        return [
            {'role':r['role'],'content':r['content'],'created_at':r['created_at'],
             'metadata':json.loads(r['metadata_json'] or '{}')}
            for r in reversed(rows)
        ]


class AgentRunRepository:
    def __init__(self,conn): self.conn=conn
    def start(self,agent_id,task_id,model,input_data):
        rid=str(uuid4())
        self.conn.execute(
            'INSERT INTO agent_runs(agent_run_id,agent_id,task_id,status,model,started_at,input_json,activity,progress) VALUES(?,?,?,?,?,?,?,?,?)',
            (rid,agent_id,task_id,'running',model,now(),json.dumps(input_data,ensure_ascii=False),'Iniciando',0.0)
        ); self.conn.commit(); return rid
    def update_activity(self,rid,activity,progress=None):
        if progress is None:
            self.conn.execute('UPDATE agent_runs SET activity=? WHERE agent_run_id=?',(activity,rid))
        else:
            self.conn.execute(
                'UPDATE agent_runs SET activity=?,progress=? WHERE agent_run_id=?',
                (activity,max(0.0,min(1.0,float(progress))),rid)
            )
        self.conn.commit()
    def finish(self,rid,*,artifact_id=None,error=None):
        self.conn.execute(
            'UPDATE agent_runs SET status=?,ended_at=?,output_artifact_id=?,last_error=?,activity=?,progress=? WHERE agent_run_id=?',
            ('failed' if error else 'completed',now(),artifact_id,error,'Erro' if error else 'Concluído',1.0 if not error else 0.0,rid)
        ); self.conn.commit()
    def latest_statuses(self):
        rows=self.conn.execute(
            'SELECT a.agent_id,a.status FROM agent_runs a JOIN '
            '(SELECT agent_id,MAX(started_at) max_started FROM agent_runs GROUP BY agent_id) x '
            'ON a.agent_id=x.agent_id AND a.started_at=x.max_started'
        ).fetchall()
        return {r['agent_id']:r['status'] for r in rows}
    def latest_runs(self):
        rows=self.conn.execute(
            'SELECT a.* FROM agent_runs a JOIN '
            '(SELECT agent_id,MAX(started_at) max_started FROM agent_runs GROUP BY agent_id) x '
            'ON a.agent_id=x.agent_id AND a.started_at=x.max_started'
        ).fetchall()
        return {r['agent_id']:dict(r) for r in rows}


class ArtifactRepository:
    def __init__(self,conn): self.conn=conn
    def add(self,*,task_id,agent_id,artifact_type,name,relative_path,checksum,metadata=None):
        aid=str(uuid4())
        self.conn.execute(
            'INSERT INTO artifacts(artifact_id,task_id,agent_id,artifact_type,name,relative_path,checksum,created_at,metadata_json) '
            'VALUES(?,?,?,?,?,?,?,?,?)',
            (aid,task_id,agent_id,artifact_type,name,relative_path,checksum,now(),json.dumps(metadata or {},ensure_ascii=False))
        ); self.conn.commit(); return aid
    def by_task(self,task_id):
        return [dict(r) for r in self.conn.execute(
            'SELECT * FROM artifacts WHERE task_id=? ORDER BY created_at',(task_id,)
        ).fetchall()]
    def recent(self,limit=10):
        return [dict(r) for r in self.conn.execute(
            'SELECT * FROM artifacts ORDER BY created_at DESC LIMIT ?',(limit,)
        ).fetchall()]


class MemoryRepository:
    def __init__(self,conn): self.conn=conn
    def add(self,content,*,memory_type='semantic',source='user',source_ref=None,confidence=1.0,scope='global',project_id=None,importance=.5,metadata=None):
        mid=str(uuid4())
        self.conn.execute(
            'INSERT INTO memories(memory_id,memory_type,content,source,source_ref,confidence,scope,project_id,importance,created_at,metadata_json) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (mid,memory_type,content,source,source_ref,confidence,scope,project_id,importance,now(),json.dumps(metadata or {},ensure_ascii=False))
        ); self.conn.commit(); return mid
    def search(self,query,limit=8):
        return [dict(r) for r in self.conn.execute(
            'SELECT * FROM memories WHERE content LIKE ? ORDER BY importance DESC,created_at DESC LIMIT ?',
            (f'%{query}%',limit)
        ).fetchall()]
    def recent(self,limit=8):
        return [dict(r) for r in self.conn.execute(
            'SELECT * FROM memories ORDER BY importance DESC,created_at DESC LIMIT ?',(limit,)
        ).fetchall()]


class ApprovalRepository:
    def __init__(self,conn): self.conn=conn
    def request(self,task_id,action,risk,payload):
        aid=str(uuid4())
        self.conn.execute(
            'INSERT INTO approvals(approval_id,task_id,action,risk,status,requested_at,payload_json) VALUES(?,?,?,?,?,?,?)',
            (aid,task_id,action,risk,'pending',now(),json.dumps(payload,ensure_ascii=False))
        ); self.conn.commit(); return aid
    def _row(self,row):
        if row is None: return None
        item=dict(row)
        try: item['payload']=json.loads(item.pop('payload_json') or '{}')
        except Exception: item['payload']={}
        return item
    def get(self,approval_id):
        return self._row(self.conn.execute(
            'SELECT * FROM approvals WHERE approval_id=?',(approval_id,)
        ).fetchone())
    def pending(self,limit=20):
        return [self._row(r) for r in self.conn.execute(
            "SELECT * FROM approvals WHERE status='pending' ORDER BY requested_at LIMIT ?",(limit,)
        ).fetchall()]
    def resolve(self,approval_id,status):
        if status not in {'approved','rejected'}: raise ValueError(status)
        self.conn.execute(
            'UPDATE approvals SET status=?,resolved_at=? WHERE approval_id=?',
            (status,now(),approval_id)
        ); self.conn.commit()
        return self.get(approval_id)


class ToolRunRepository:
    def __init__(self,conn): self.conn=conn
    def start(self,task_id,tool_id,payload):
        rid=str(uuid4())
        self.conn.execute(
            'INSERT INTO tool_runs(tool_run_id,task_id,tool_id,status,started_at,input_json) VALUES(?,?,?,?,?,?)',
            (rid,task_id,tool_id,'running',now(),json.dumps(payload,ensure_ascii=False))
        ); self.conn.commit(); return rid
    def finish(self,run_id,*,status,output=None,evidence=None,error=None):
        self.conn.execute(
            'UPDATE tool_runs SET status=?,ended_at=?,output_json=?,evidence_json=?,error=? WHERE tool_run_id=?',
            (
                status,now(),
                json.dumps(output or {},ensure_ascii=False),
                json.dumps(evidence or {},ensure_ascii=False),
                error,run_id
            )
        ); self.conn.commit()
    def recent(self,limit=30):
        rows=self.conn.execute(
            'SELECT * FROM tool_runs ORDER BY started_at DESC LIMIT ?',(limit,)
        ).fetchall()
        result=[]
        for r in rows:
            item=dict(r)
            for key in ('input_json','output_json','evidence_json'):
                try: item[key[:-5] if key.endswith('_json') else key]=json.loads(item.get(key) or '{}')
                except Exception: item[key[:-5] if key.endswith('_json') else key]={}
            result.append(item)
        return result

class MissionRepository:
    def __init__(self,conn): self.conn=conn
    def create(self,task_id,title,objective,workspace_id=None,metadata=None):
        mid=str(uuid4()); ts=now()
        self.conn.execute(
            'INSERT INTO missions(mission_id,task_id,workspace_id,title,objective,status,created_at,updated_at,metadata_json) '
            'VALUES(?,?,?,?,?,?,?,?,?)',
            (mid,task_id,workspace_id,title,objective,'running',ts,ts,json.dumps(metadata or {},ensure_ascii=False))
        ); self.conn.commit(); return mid
    def add_step(self,mission_id,sequence,agent_id,input_artifact_id=None,metadata=None):
        sid=str(uuid4())
        self.conn.execute(
            'INSERT INTO mission_steps(step_id,mission_id,sequence,agent_id,status,input_artifact_id,metadata_json) '
            'VALUES(?,?,?,?,?,?,?)',
            (sid,mission_id,sequence,agent_id,'waiting',input_artifact_id,json.dumps(metadata or {},ensure_ascii=False))
        ); self.conn.commit(); return sid
    def start_step(self,step_id):
        self.conn.execute(
            "UPDATE mission_steps SET status='running',started_at=? WHERE step_id=?",
            (now(),step_id)
        ); self.conn.commit()
    def finish_step(self,step_id,artifact_id=None,error=None):
        self.conn.execute(
            'UPDATE mission_steps SET status=?,ended_at=?,output_artifact_id=?,error=? WHERE step_id=?',
            ('failed' if error else 'completed',now(),artifact_id,error,step_id)
        ); self.conn.commit()
    def complete(self,mission_id,error=None):
        status='failed' if error else 'completed'; ts=now()
        self.conn.execute(
            'UPDATE missions SET status=?,updated_at=?,completed_at=? WHERE mission_id=?',
            (status,ts,ts,mission_id)
        ); self.conn.commit()
    def active(self,limit=20):
        rows=self.conn.execute(
            "SELECT * FROM missions WHERE status NOT IN ('completed','failed','cancelled') ORDER BY updated_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [self.with_steps(dict(r)) for r in rows]
    def recent(self,limit=20):
        rows=self.conn.execute(
            'SELECT * FROM missions ORDER BY created_at DESC LIMIT ?',(limit,)
        ).fetchall()
        return [self.with_steps(dict(r)) for r in rows]
    def with_steps(self,mission):
        mission['metadata']=json.loads(mission.pop('metadata_json') or '{}')
        mission['steps']=[dict(r) for r in self.conn.execute(
            'SELECT * FROM mission_steps WHERE mission_id=? ORDER BY sequence',(mission['mission_id'],)
        ).fetchall()]
        return mission


class WorkspaceRepository:
    def __init__(self,conn): self.conn=conn
    def get_or_create_default(self):
        row=self.conn.execute(
            "SELECT * FROM workspaces WHERE name='Principal' ORDER BY created_at LIMIT 1"
        ).fetchone()
        if row: return dict(row)
        wid=str(uuid4()); ts=now()
        self.conn.execute(
            'INSERT INTO workspaces(workspace_id,name,description,created_at,updated_at,metadata_json) VALUES(?,?,?,?,?,?)',
            (wid,'Principal','Workspace padrão do Jarvis Next',ts,ts,'{}')
        ); self.conn.commit()
        return dict(self.conn.execute('SELECT * FROM workspaces WHERE workspace_id=?',(wid,)).fetchone())
    def list(self):
        return [dict(r) for r in self.conn.execute(
            'SELECT * FROM workspaces ORDER BY updated_at DESC'
        ).fetchall()]


class ProjectRepository:
    def __init__(self,conn): self.conn=conn

    def create(self,name,objective='',workspace_id=None,metadata=None):
        pid=str(uuid4()); ts=now()
        self.conn.execute(
            'INSERT INTO projects(project_id,workspace_id,name,objective,status,created_at,updated_at,metadata_json) '
            'VALUES(?,?,?,?,?,?,?,?)',
            (pid,workspace_id,name,objective,'active',ts,ts,json.dumps(metadata or {},ensure_ascii=False))
        ); self.conn.commit()
        return self.get(pid)

    def get(self,project_id):
        row=self.conn.execute('SELECT * FROM projects WHERE project_id=?',(project_id,)).fetchone()
        if row is None: raise KeyError(project_id)
        item=dict(row)
        item['metadata']=json.loads(item.pop('metadata_json') or '{}')
        return item

    def update(self,project_id,*,name=None,objective=None,status=None,metadata=None):
        current=self.get(project_id)
        name=current['name'] if name is None else name
        objective=current['objective'] if objective is None else objective
        status=current['status'] if status is None else status
        merged=dict(current.get('metadata') or {})
        if metadata: merged.update(metadata)
        self.conn.execute(
            'UPDATE projects SET name=?,objective=?,status=?,updated_at=?,metadata_json=? WHERE project_id=?',
            (name,objective,status,now(),json.dumps(merged,ensure_ascii=False),project_id)
        ); self.conn.commit()
        return self.get(project_id)

    def list(self,workspace_id=None,limit=100):
        if workspace_id:
            rows=self.conn.execute(
                'SELECT * FROM projects WHERE workspace_id=? ORDER BY updated_at DESC LIMIT ?',
                (workspace_id,limit)
            ).fetchall()
        else:
            rows=self.conn.execute(
                'SELECT * FROM projects ORDER BY updated_at DESC LIMIT ?',(limit,)
            ).fetchall()
        result=[]
        for row in rows:
            item=dict(row)
            item['metadata']=json.loads(item.pop('metadata_json') or '{}')
            result.append(item)
        return result


class WorkspaceNoteRepository:
    def __init__(self,conn): self.conn=conn

    def create(self,workspace_id,title,content):
        nid=str(uuid4()); ts=now()
        self.conn.execute(
            'INSERT INTO workspace_notes(note_id,workspace_id,title,content,created_at,updated_at) VALUES(?,?,?,?,?,?)',
            (nid,workspace_id,title,content,ts,ts)
        ); self.conn.commit()
        return nid

    def list(self,workspace_id,limit=100):
        return [dict(r) for r in self.conn.execute(
            'SELECT * FROM workspace_notes WHERE workspace_id=? ORDER BY updated_at DESC LIMIT ?',
            (workspace_id,limit)
        ).fetchall()]
