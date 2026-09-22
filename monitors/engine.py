import hashlib
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
import xml.etree.ElementTree as ET

import requests


class MonitorEngine:
    """
    Watches persistentes e baratos. Não roda sozinho; o AutomationEngine pode
    agendar monitor.check / monitor.check_all.
    """

    def __init__(self, db_path, knowledge=None, wordpress=None, user_agent="JarvisSindPet/0.9"):
        self.db_path=Path(db_path);self.db_path.parent.mkdir(parents=True,exist_ok=True)
        self.knowledge=knowledge;self.wordpress=wordpress;self.user_agent=user_agent
        self.notifier=None
        self.session=requests.Session();self.session.headers.update({"User-Agent":user_agent})
        self._init_db()


    def set_notifier(self,callback):
        self.notifier=callback
        return {"ok":True}
    def _connect(self):
        c=sqlite3.connect(self.db_path,timeout=20);c.row_factory=sqlite3.Row;return c
    def _now(self):return datetime.now().isoformat(timespec="seconds")

    def _init_db(self):
        with self._connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS monitors(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE,
              monitor_type TEXT NOT NULL,
              config_json TEXT NOT NULL DEFAULT '{}',
              status TEXT NOT NULL DEFAULT 'enabled',
              last_check TEXT,last_change TEXT,last_hash TEXT,last_value_json TEXT NOT NULL DEFAULT '{}',
              check_count INTEGER NOT NULL DEFAULT 0,change_count INTEGER NOT NULL DEFAULT 0,
              error_count INTEGER NOT NULL DEFAULT 0,last_error TEXT,
              tags TEXT DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_monitors_type ON monitors(monitor_type,status);
            CREATE TABLE IF NOT EXISTS monitor_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,monitor_id INTEGER NOT NULL,
              created_at TEXT NOT NULL,event_type TEXT NOT NULL,
              previous_hash TEXT,new_hash TEXT,summary TEXT DEFAULT '',
              payload_json TEXT NOT NULL DEFAULT '{}',acknowledged INTEGER NOT NULL DEFAULT 0,
              FOREIGN KEY(monitor_id) REFERENCES monitors(id));
            CREATE INDEX IF NOT EXISTS idx_monitor_events ON monitor_events(monitor_id,id DESC);
            """)

    def _row(self,row):
        if not row:return None
        d=dict(row)
        for src,dst in [("config_json","config"),("last_value_json","last_value")]:
            try:d[dst]=json.loads(d.pop(src) or "{}")
            except Exception:d[dst]={}
        d["tags"]=[x.strip() for x in (d.get("tags") or "").split(",") if x.strip()]
        return d
    def _rows(self,rows):return [self._row(x) for x in rows]
    def _hash(self,value):
        raw=json.dumps(value,ensure_ascii=False,sort_keys=True,default=str) if not isinstance(value,(str,bytes)) else value
        if isinstance(raw,str):raw=raw.encode("utf-8",errors="replace")
        return hashlib.sha256(raw).hexdigest()

    def create(self,name,monitor_type,config,tags=None,enabled=True):
        now=self._now()
        try:
            with self._connect() as c:
                cur=c.execute(
                    """INSERT INTO monitors(name,monitor_type,config_json,status,tags,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?)""",
                    (str(name).strip(),str(monitor_type).lower(),json.dumps(config or {},ensure_ascii=False),
                     "enabled" if enabled else "disabled",
                     ",".join(tags or []) if isinstance(tags,list) else str(tags or ""),now,now)
                )
            return self.get(cur.lastrowid)
        except sqlite3.IntegrityError:
            return {"ok":False,"error":f"Já existe monitor chamado '{name}'."}

    def get(self,monitor_id=None,name=None):
        with self._connect() as c:
            if monitor_id is not None:r=c.execute("SELECT * FROM monitors WHERE id=?",(int(monitor_id),)).fetchone()
            else:r=c.execute("SELECT * FROM monitors WHERE name=?",(str(name),)).fetchone()
        return {"ok":bool(r),"data":self._row(r),"error":None if r else "Monitor não encontrado."}

    def list(self,monitor_type=None,status=None,tag=None,limit=200):
        sql="SELECT * FROM monitors WHERE 1=1";args=[]
        if monitor_type:sql+=" AND monitor_type=?";args.append(str(monitor_type))
        if status:sql+=" AND status=?";args.append(str(status))
        if tag:sql+=" AND (','||tags||',') LIKE ?";args.append(f"%,{tag},%")
        sql+=" ORDER BY id DESC LIMIT ?";args.append(int(limit))
        with self._connect() as c:rows=c.execute(sql,args).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def update(self,monitor_id,**fields):
        sets=[];args=[]
        for k in ("name","monitor_type","status"):
            if k in fields and fields[k] is not None:sets.append(f"{k}=?");args.append(fields[k])
        if "config" in fields and fields["config"] is not None:
            sets.append("config_json=?");args.append(json.dumps(fields["config"],ensure_ascii=False))
        if "tags" in fields and fields["tags"] is not None:
            tags=fields["tags"];sets.append("tags=?");args.append(",".join(tags) if isinstance(tags,list) else str(tags))
        if not sets:return self.get(monitor_id)
        sets.append("updated_at=?");args.append(self._now());args.append(int(monitor_id))
        try:
            with self._connect() as c:c.execute(f"UPDATE monitors SET {','.join(sets)} WHERE id=?",args)
        except sqlite3.IntegrityError as exc:return {"ok":False,"error":str(exc)}
        return self.get(monitor_id)

    def enable(self,monitor_id):return self.update(monitor_id,status="enabled")
    def disable(self,monitor_id):return self.update(monitor_id,status="disabled")
    def mute(self,monitor_id):return self.update(monitor_id,status="muted")
    def unmute(self,monitor_id):return self.update(monitor_id,status="enabled")

    def delete(self,monitor_id):
        with self._connect() as c:
            c.execute("DELETE FROM monitor_events WHERE monitor_id=?",(int(monitor_id),))
            cur=c.execute("DELETE FROM monitors WHERE id=?",(int(monitor_id),))
        return {"ok":cur.rowcount>0,"id":int(monitor_id)}

    def _website(self,cfg):
        url=str(cfg.get("url","")).strip()
        if not url.startswith("https://"):
            raise ValueError("Website monitor aceita apenas HTTPS.")
        r=self.session.get(url,timeout=int(cfg.get("timeout",20)),allow_redirects=True)
        text=r.text
        mode=cfg.get("mode","body")
        if mode=="status":
            value={"url":r.url,"status":r.status_code}
        elif mode=="headers":
            keys=cfg.get("headers",["etag","last-modified","content-length"])
            value={"url":r.url,"status":r.status_code,"headers":{k:r.headers.get(k,"") for k in keys}}
        else:
            # normaliza espaços para reduzir falsos positivos
            import re
            body=re.sub(r"\s+"," ",text).strip()
            contains=cfg.get("contains")
            if contains:
                value={"url":r.url,"status":r.status_code,"contains":str(contains) in body}
            else:
                max_chars=int(cfg.get("max_chars",200000))
                value={"url":r.url,"status":r.status_code,"body":body[:max_chars]}
        return value

    def _rss(self,cfg):
        url=str(cfg.get("url","")).strip()
        if not url.startswith("https://"):raise ValueError("RSS monitor aceita apenas HTTPS.")
        r=self.session.get(url,timeout=int(cfg.get("timeout",20)));r.raise_for_status()
        root=ET.fromstring(r.content)
        items=[]
        for node in root.iter():
            tag=node.tag.lower()
            if tag.endswith("item") or tag.endswith("entry"):
                title="";link="";date=""
                for child in list(node):
                    ct=child.tag.lower()
                    if ct.endswith("title"):title=(child.text or "").strip()
                    elif ct.endswith("link"):
                        link=(child.get("href") or child.text or "").strip()
                    elif ct.endswith("pubdate") or ct.endswith("updated") or ct.endswith("published"):
                        date=(child.text or "").strip()
                items.append({"title":title,"link":link,"date":date})
        limit=int(cfg.get("limit",20))
        return {"items":items[:limit],"count":len(items)}

    def _file(self,cfg):
        p=Path(cfg.get("path","")).expanduser().resolve()
        if not p.is_file():return {"exists":False,"path":str(p)}
        st=p.stat()
        mode=cfg.get("mode","metadata")
        value={"exists":True,"path":str(p),"size":st.st_size,"mtime":st.st_mtime}
        if mode=="hash":
            h=hashlib.sha256()
            with p.open("rb") as f:
                for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
            value["sha256"]=h.hexdigest()
        return value

    def _folder(self,cfg):
        p=Path(cfg.get("path","")).expanduser().resolve()
        if not p.is_dir():return {"exists":False,"path":str(p)}
        recursive=bool(cfg.get("recursive",False));pattern=str(cfg.get("pattern","*"))
        iterator=p.rglob(pattern) if recursive else p.glob(pattern)
        items=[]
        for x in iterator:
            try:
                if x.is_file():
                    s=x.stat();items.append({"path":str(x.relative_to(p)),"size":s.st_size,"mtime":int(s.st_mtime)})
            except Exception:continue
        items.sort(key=lambda x:x["path"].lower())
        return {"exists":True,"path":str(p),"count":len(items),"items":items[:int(cfg.get("max_items",2000))]}

    def _knowledge(self,cfg):
        if not self.knowledge:raise RuntimeError("Knowledge Base indisponível.")
        collection=str(cfg.get("collection","")).strip()
        docs=self.knowledge.list_documents(collection,limit=int(cfg.get("limit",500)))
        return {"collection":collection,"count":docs.get("count",0),
                "documents":[{"id":x.get("id"),"title":x.get("title"),"created_at":x.get("created_at")} for x in docs.get("items",[])]}

    def _wordpress(self,cfg):
        if not self.wordpress:raise RuntimeError("WordPress Manager indisponível.")
        profile=cfg.get("profile","default");resource=cfg.get("resource","posts")
        operation={"posts":"list_posts","pages":"list_pages","media":"list_media","comments":"list_comments"}.get(resource)
        if not operation:raise ValueError("resource WordPress inválido.")
        r=self.wordpress.execute(operation,profile=profile,per_page=int(cfg.get("per_page",20)))
        if not r.get("ok"):raise RuntimeError(str(r.get("error")))
        data=r.get("data",[])
        compact=[]
        for x in data if isinstance(data,list) else []:
            compact.append({"id":x.get("id"),"date":x.get("date"),"modified":x.get("modified"),
                            "status":x.get("status"),"slug":x.get("slug")})
        return {"profile":profile,"resource":resource,"items":compact}

    def _compute(self,monitor):
        typ=monitor["monitor_type"];cfg=monitor["config"]
        if typ=="website":return self._website(cfg)
        if typ=="rss":return self._rss(cfg)
        if typ=="file":return self._file(cfg)
        if typ=="folder":return self._folder(cfg)
        if typ=="knowledge":return self._knowledge(cfg)
        if typ=="wordpress":return self._wordpress(cfg)
        raise ValueError(f"Tipo de monitor desconhecido: {typ}")

    def check(self,monitor_id,force=False):
        mon=self.get(monitor_id).get("data")
        if not mon:return {"ok":False,"error":"Monitor não encontrado."}
        if mon["status"]=="disabled" and not force:return {"ok":False,"error":"Monitor desabilitado."}
        try:
            value=self._compute(mon);new_hash=self._hash(value);previous=mon.get("last_hash")
            changed=bool(previous and previous!=new_hash)
            now=self._now()
            with self._connect() as c:
                c.execute(
                    """UPDATE monitors SET last_check=?,last_hash=?,last_value_json=?,
                       check_count=check_count+1,last_error=NULL,
                       error_count=CASE WHEN error_count>0 THEN error_count-1 ELSE 0 END,
                       last_change=CASE WHEN ? THEN ? ELSE last_change END,
                       change_count=change_count+? ,updated_at=? WHERE id=?""",
                    (now,new_hash,json.dumps(value,ensure_ascii=False,default=str),
                     1 if changed else 0,now,1 if changed else 0,now,int(monitor_id))
                )
                event_id=None
                if changed:
                    summary=f"{mon['name']} detectou alteração em {mon['monitor_type']}."
                    cur=c.execute(
                        """INSERT INTO monitor_events(monitor_id,created_at,event_type,previous_hash,new_hash,summary,payload_json)
                           VALUES(?,?,?,?,?,?,?)""",
                        (int(monitor_id),now,"changed",previous,new_hash,summary,
                         json.dumps(value,ensure_ascii=False,default=str))
                    );event_id=int(cur.lastrowid)
            result={"ok":True,"monitor_id":int(monitor_id),"changed":changed,"event_id":event_id,
                    "name":mon["name"],"type":mon["monitor_type"],"value":value}
            if changed and self.notifier:
                try:self.notifier(mon,result)
                except Exception:pass
            return result
        except Exception as exc:
            with self._connect() as c:
                c.execute(
                    """UPDATE monitors SET last_check=?,last_error=?,error_count=error_count+1,
                       updated_at=? WHERE id=?""",
                    (self._now(),str(exc)[:4000],self._now(),int(monitor_id))
                )
            return {"ok":False,"monitor_id":int(monitor_id),"error":str(exc)}

    def check_all(self,monitor_type=None,limit=200):
        items=self.list(monitor_type=monitor_type,status="enabled",limit=limit)["items"]
        results=[self.check(x["id"]) for x in items]
        return {"ok":True,"checked":len(results),"changes":sum(1 for x in results if x.get("changed")),"results":results}

    def events(self,monitor_id=None,acknowledged=None,limit=200):
        sql="""SELECT e.*,m.name monitor_name,m.monitor_type FROM monitor_events e
               JOIN monitors m ON m.id=e.monitor_id WHERE 1=1""";args=[]
        if monitor_id is not None:sql+=" AND e.monitor_id=?";args.append(int(monitor_id))
        if acknowledged is not None:sql+=" AND e.acknowledged=?";args.append(1 if acknowledged else 0)
        sql+=" ORDER BY e.id DESC LIMIT ?";args.append(int(limit))
        with self._connect() as c:rows=c.execute(sql,args).fetchall()
        out=[]
        for r in rows:
            d=dict(r)
            try:d["payload"]=json.loads(d.pop("payload_json") or "{}")
            except Exception:d["payload"]={}
            d["acknowledged"]=bool(d["acknowledged"]);out.append(d)
        return {"ok":True,"items":out,"count":len(out)}

    def acknowledge(self,event_id):
        with self._connect() as c:cur=c.execute("UPDATE monitor_events SET acknowledged=1 WHERE id=?",(int(event_id),))
        return {"ok":cur.rowcount>0,"event_id":int(event_id)}

    def acknowledge_all(self,monitor_id=None):
        with self._connect() as c:
            if monitor_id is None:cur=c.execute("UPDATE monitor_events SET acknowledged=1 WHERE acknowledged=0")
            else:cur=c.execute("UPDATE monitor_events SET acknowledged=1 WHERE acknowledged=0 AND monitor_id=?",(int(monitor_id),))
        return {"ok":True,"updated":cur.rowcount}

    def clear_events(self,acknowledged_only=True):
        with self._connect() as c:
            if acknowledged_only:cur=c.execute("DELETE FROM monitor_events WHERE acknowledged=1")
            else:cur=c.execute("DELETE FROM monitor_events")
        return {"ok":True,"removed":cur.rowcount}

    def snapshot(self,monitor_id):
        d=self.get(monitor_id).get("data")
        if not d:return {"ok":False,"error":"Monitor não encontrado."}
        return {"ok":True,"monitor":d,"recent_events":self.events(monitor_id=monitor_id,limit=10)["items"]}

    def stats(self):
        with self._connect() as c:
            total=c.execute("SELECT COUNT(*) n FROM monitors").fetchone()["n"]
            types=c.execute("SELECT monitor_type,COUNT(*) n FROM monitors GROUP BY monitor_type").fetchall()
            statuses=c.execute("SELECT status,COUNT(*) n FROM monitors GROUP BY status").fetchall()
            pending=c.execute("SELECT COUNT(*) n FROM monitor_events WHERE acknowledged=0").fetchone()["n"]
        return {"ok":True,"monitors":total,"pending_events":pending,
                "types":{r["monitor_type"]:r["n"] for r in types},
                "statuses":{r["status"]:r["n"] for r in statuses}}

    def export(self,path):
        out=Path(path).expanduser().resolve();out.parent.mkdir(parents=True,exist_ok=True)
        data=self.list(limit=10000)["items"];out.write_text(json.dumps(data,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
        return {"ok":True,"path":str(out),"monitors":len(data)}

    def import_(self,path,overwrite=False):
        p=Path(path).expanduser().resolve()
        if not p.is_file():return {"ok":False,"error":"Arquivo não encontrado."}
        try:data=json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:return {"ok":False,"error":str(exc)}
        created=[];errors=[]
        for x in data if isinstance(data,list) else []:
            if overwrite:
                existing=self.get(name=x.get("name")).get("data")
                if existing:self.delete(existing["id"])
            r=self.create(x.get("name"),x.get("monitor_type"),x.get("config",{}),tags=x.get("tags",[]),
                          enabled=x.get("status","enabled")=="enabled")
            (created if r.get("ok") else errors).append(r)
        return {"ok":not errors,"created":len(created),"errors":errors}

    def execute(self,operation,**params):
        mapping={
          "create":self.create,"get":self.get,"list":self.list,"update":self.update,
          "enable":self.enable,"disable":self.disable,"mute":self.mute,"unmute":self.unmute,
          "delete":self.delete,"check":self.check,"check_all":self.check_all,
          "events":self.events,"acknowledge":self.acknowledge,"acknowledge_all":self.acknowledge_all,
          "clear_events":self.clear_events,"snapshot":self.snapshot,"stats":self.stats,
          "export":self.export,"import":self.import_,
        }
        fn=mapping.get(operation)
        if not fn:return {"ok":False,"error":f"Operação de monitor desconhecida: {operation}"}
        return fn(**params)
