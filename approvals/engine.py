import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


class ApprovalEngine:
    def __init__(self, db_path):
        self.db_path=Path(db_path);self.db_path.parent.mkdir(parents=True,exist_ok=True)
        self._executor=None
        self._resolution_callback=None
        self._init_db()

    def _connect(self):
        c=sqlite3.connect(self.db_path,timeout=20);c.row_factory=sqlite3.Row;return c
    def _now(self):return datetime.now()
    def _iso(self,dt=None):return (dt or self._now()).isoformat(timespec="seconds")

    def _init_db(self):
        with self._connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS approvals(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL,description TEXT DEFAULT '',
              source_type TEXT NOT NULL,source_id TEXT DEFAULT '',
              action_id TEXT DEFAULT '',payload_json TEXT NOT NULL DEFAULT '{}',
              risk TEXT NOT NULL DEFAULT 'high',status TEXT NOT NULL DEFAULT 'pending',
              requested_at TEXT NOT NULL,expires_at TEXT,
              resolved_at TEXT,resolved_by TEXT,resolution_note TEXT DEFAULT '',
              execution_json TEXT NOT NULL DEFAULT '{}');
            CREATE INDEX IF NOT EXISTS idx_approvals_status ON approvals(status,requested_at);
            """)

    def set_executor(self,callback):self._executor=callback;return {"ok":True}
    def set_resolution_callback(self,callback):
        self._resolution_callback=callback
        return {"ok":True}

    def _row(self,row):
        if not row:return None
        d=dict(row)
        for src,dst in [("payload_json","payload"),("execution_json","execution")]:
            try:d[dst]=json.loads(d.pop(src) or "{}")
            except Exception:d[dst]={}
        return d
    def _rows(self,rows):return [self._row(r) for r in rows]

    def create(self,title,source_type,source_id="",action_id="",payload=None,risk="high",
               description="",expires_minutes=None):
        expires=None
        if expires_minutes is not None:
            expires=self._iso(self._now()+timedelta(minutes=float(expires_minutes)))
        with self._connect() as c:
            cur=c.execute(
                """INSERT INTO approvals(title,description,source_type,source_id,action_id,
                   payload_json,risk,status,requested_at,expires_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (str(title),str(description),str(source_type),str(source_id),str(action_id),
                 json.dumps(payload or {},ensure_ascii=False,default=str),str(risk),"pending",
                 self._iso(),expires)
            )
            approval_id=int(cur.lastrowid)
        return self.get(approval_id)

    def get(self,approval_id):
        self.expire_due()
        with self._connect() as c:r=c.execute("SELECT * FROM approvals WHERE id=?",(int(approval_id),)).fetchone()
        return {"ok":bool(r),"data":self._row(r),"error":None if r else "Aprovação não encontrada."}

    def list(self,status=None,risk=None,source_type=None,limit=200):
        self.expire_due()
        sql="SELECT * FROM approvals WHERE 1=1";args=[]
        if status:sql+=" AND status=?";args.append(str(status))
        if risk:sql+=" AND risk=?";args.append(str(risk))
        if source_type:sql+=" AND source_type=?";args.append(str(source_type))
        sql+=" ORDER BY id DESC LIMIT ?";args.append(int(limit))
        with self._connect() as c:rows=c.execute(sql,args).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def pending(self,limit=200):return self.list(status="pending",limit=limit)

    def _resolve(self,approval_id,status,resolved_by="user",note=""):
        current=self.get(approval_id).get("data")
        if not current:return {"ok":False,"error":"Aprovação não encontrada."}
        if current["status"]!="pending":
            return {"ok":False,"error":f"Aprovação está {current['status']}."}
        with self._connect() as c:
            c.execute(
                """UPDATE approvals SET status=?,resolved_at=?,resolved_by=?,resolution_note=?
                   WHERE id=?""",
                (status,self._iso(),str(resolved_by),str(note),int(approval_id))
            )
        return self.get(approval_id)

    def approve(self,approval_id,resolved_by="user",note="",execute=True):
        resolved=self._resolve(approval_id,"approved",resolved_by,note)
        if not resolved.get("ok"):return resolved
        item=resolved["data"]
        execution=None
        if execute and self._executor:
            try:
                execution=self._executor(item)
            except Exception as exc:
                execution={"ok":False,"error":str(exc)}
            with self._connect() as c:
                c.execute(
                    "UPDATE approvals SET execution_json=? WHERE id=?",
                    (json.dumps(execution or {},ensure_ascii=False,default=str),int(approval_id))
                )
        out=self.get(approval_id)
        out["execution"]=execution
        return out

    def reject(self,approval_id,resolved_by="user",note=""):
        result=self._resolve(approval_id,"rejected",resolved_by,note)
        if result.get("ok") and self._resolution_callback:
            try:self._resolution_callback(result["data"])
            except Exception:pass
        return result

    def cancel(self,approval_id,note=""):
        result=self._resolve(approval_id,"cancelled","system",note)
        if result.get("ok") and self._resolution_callback:
            try:self._resolution_callback(result["data"])
            except Exception:pass
        return result

    def reopen(self,approval_id):
        item=self.get(approval_id).get("data")
        if not item:return {"ok":False,"error":"Aprovação não encontrada."}
        if item["status"]=="pending":return self.get(approval_id)
        with self._connect() as c:
            c.execute(
                """UPDATE approvals SET status='pending',resolved_at=NULL,resolved_by=NULL,
                   resolution_note='',execution_json='{}' WHERE id=?""",
                (int(approval_id),)
            )
        return self.get(approval_id)

    def expire_due(self):
        now=self._iso()
        expired_items=[]
        with self._connect() as c:
            rows=c.execute(
                """SELECT id FROM approvals WHERE status='pending'
                   AND expires_at IS NOT NULL AND expires_at<?""",
                (now,)
            ).fetchall()
            ids=[int(r["id"]) for r in rows]
            for approval_id in ids:
                c.execute(
                    """UPDATE approvals SET status='expired',resolved_at=?,resolved_by='system',
                       resolution_note='Prazo de aprovação expirou.' WHERE id=?""",
                    (now,approval_id)
                )
        if self._resolution_callback:
            for approval_id in ids:
                try:
                    item=self.get(approval_id).get("data")
                    if item:
                        self._resolution_callback(item)
                except Exception:
                    pass
        return {"ok":True,"expired":len(ids)}

    def delete(self,approval_id):
        item=self.get(approval_id).get("data")
        if not item:return {"ok":False,"error":"Aprovação não encontrada."}
        if item["status"]=="pending":
            return {"ok":False,"error":"Não é permitido apagar uma aprovação pendente; cancele primeiro."}
        with self._connect() as c:cur=c.execute("DELETE FROM approvals WHERE id=?",(int(approval_id),))
        return {"ok":cur.rowcount>0,"id":int(approval_id)}

    def clear_resolved(self,older_than_days=30):
        cutoff=self._iso(self._now()-timedelta(days=float(older_than_days)))
        with self._connect() as c:
            cur=c.execute(
                """DELETE FROM approvals WHERE status!='pending'
                   AND COALESCE(resolved_at,requested_at)<?""",
                (cutoff,)
            )
        return {"ok":True,"removed":cur.rowcount}

    def stats(self):
        self.expire_due()
        with self._connect() as c:
            total=c.execute("SELECT COUNT(*) n FROM approvals").fetchone()["n"]
            rows=c.execute("SELECT status,COUNT(*) n FROM approvals GROUP BY status").fetchall()
            risks=c.execute("SELECT risk,COUNT(*) n FROM approvals WHERE status='pending' GROUP BY risk").fetchall()
        return {"ok":True,"approvals":total,
                "statuses":{r["status"]:r["n"] for r in rows},
                "pending_by_risk":{r["risk"]:r["n"] for r in risks}}

    def search(self,query,limit=100):
        q=f"%{str(query).strip()}%"
        with self._connect() as c:
            rows=c.execute(
                """SELECT * FROM approvals WHERE title LIKE ? OR description LIKE ?
                   OR action_id LIKE ? OR source_id LIKE ? ORDER BY id DESC LIMIT ?""",
                (q,q,q,q,int(limit))
            ).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def export(self,path,limit=10000):
        out=Path(path).expanduser().resolve();out.parent.mkdir(parents=True,exist_ok=True)
        data=self.list(limit=limit)["items"]
        out.write_text(json.dumps(data,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
        return {"ok":True,"path":str(out),"approvals":len(data)}

    def execute(self,operation,**params):
        mapping={
          "create":self.create,"get":self.get,"list":self.list,"pending":self.pending,
          "approve":self.approve,"reject":self.reject,"cancel":self.cancel,"reopen":self.reopen,
          "expire_due":self.expire_due,"delete":self.delete,"clear_resolved":self.clear_resolved,
          "stats":self.stats,"search":self.search,"export":self.export,
        }
        fn=mapping.get(operation)
        if not fn:return {"ok":False,"error":f"Operação de aprovação desconhecida: {operation}"}
        return fn(**params)
