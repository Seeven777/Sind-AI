import hashlib
import hmac
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path


class TeamAssistantEngine:
    """
    Gestão local do assistente para equipe.
    Senhas são PBKDF2-SHA256; nunca ficam em texto puro.
    """

    def __init__(self,db_path):
        self.db_path=Path(db_path);self.db_path.parent.mkdir(parents=True,exist_ok=True);self._init_db()

    def _connect(self):
        c=sqlite3.connect(self.db_path,timeout=20);c.row_factory=sqlite3.Row;return c
    def _now(self):return datetime.now().isoformat(timespec="seconds")

    def _init_db(self):
        with self._connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS team_roles(
              id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,
              description TEXT DEFAULT '',status TEXT NOT NULL DEFAULT 'active',
              created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS team_users(
              id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL UNIQUE,
              display_name TEXT NOT NULL,role_id INTEGER,status TEXT NOT NULL DEFAULT 'active',
              password_hash TEXT,password_salt TEXT,notes TEXT DEFAULT '',
              created_at TEXT NOT NULL,updated_at TEXT NOT NULL,last_login TEXT,
              FOREIGN KEY(role_id) REFERENCES team_roles(id));
            CREATE TABLE IF NOT EXISTS team_collection_grants(
              id INTEGER PRIMARY KEY AUTOINCREMENT,role_id INTEGER NOT NULL,
              collection TEXT NOT NULL,access_level TEXT NOT NULL DEFAULT 'read',
              UNIQUE(role_id,collection),FOREIGN KEY(role_id) REFERENCES team_roles(id));
            CREATE TABLE IF NOT EXISTS team_track_grants(
              id INTEGER PRIMARY KEY AUTOINCREMENT,role_id INTEGER NOT NULL,
              track_id INTEGER NOT NULL,access_level TEXT NOT NULL DEFAULT 'read',
              UNIQUE(role_id,track_id),FOREIGN KEY(role_id) REFERENCES team_roles(id));
            CREATE TABLE IF NOT EXISTS team_feedback(
              id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,
              created_at TEXT NOT NULL,rating INTEGER,category TEXT DEFAULT '',
              question TEXT DEFAULT '',answer TEXT DEFAULT '',comment TEXT DEFAULT '',
              status TEXT NOT NULL DEFAULT 'open',metadata_json TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS team_gaps(
              id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,
              question TEXT NOT NULL,category TEXT DEFAULT '',source TEXT DEFAULT 'team',
              occurrences INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'open',
              resolution TEXT DEFAULT '',resolved_at TEXT);
            CREATE TABLE IF NOT EXISTS team_ask_log(
              id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER,created_at TEXT NOT NULL,
              question TEXT NOT NULL,answer TEXT DEFAULT '',sources_json TEXT NOT NULL DEFAULT '[]',
              ok INTEGER NOT NULL DEFAULT 1,latency_ms REAL,error TEXT);
            CREATE TABLE IF NOT EXISTS team_settings(
              key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at TEXT NOT NULL);
            """)
            defaults={
              "portal_name":"Sind Assist",
              "portal_host":"127.0.0.1",
              "portal_port":"8765",
              "allow_registration":"off",
              "knowledge_only_mode":"on",
              "max_sources":"6",
              "answer_timeout_seconds":"45"
            }
            now=self._now()
            for k,v in defaults.items():
                c.execute("INSERT OR IGNORE INTO team_settings(key,value,updated_at) VALUES(?,?,?)",(k,v,now))

    def _rows(self,rows):return [dict(r) for r in rows]
    def _get(self,table,item_id):
        with self._connect() as c:r=c.execute(f"SELECT * FROM {table} WHERE id=?",(int(item_id),)).fetchone()
        return {"ok":bool(r),"data":dict(r) if r else None,"error":None if r else "Registro não encontrado."}

    def role_create(self,name,description="",status="active"):
        now=self._now()
        try:
            with self._connect() as c:
                cur=c.execute(
                    "INSERT INTO team_roles(name,description,status,created_at,updated_at) VALUES(?,?,?,?,?)",
                    (str(name),str(description),str(status),now,now)
                )
            return self.role_get(cur.lastrowid)
        except sqlite3.IntegrityError:return {"ok":False,"error":"Função/role já existe."}

    def role_get(self,id):return self._get("team_roles",id)
    def role_list(self,status=None,limit=200):
        sql="SELECT * FROM team_roles";args=[]
        if status:sql+=" WHERE status=?";args.append(str(status))
        sql+=" ORDER BY name LIMIT ?";args.append(int(limit))
        with self._connect() as c:rows=c.execute(sql,args).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}
    def role_update(self,id,**fields):
        sets=[];args=[]
        for k in ("name","description","status"):
            if k in fields and fields[k] is not None:sets.append(f"{k}=?");args.append(fields[k])
        if not sets:return self.role_get(id)
        sets.append("updated_at=?");args.append(self._now());args.append(int(id))
        with self._connect() as c:c.execute(f"UPDATE team_roles SET {','.join(sets)} WHERE id=?",args)
        return self.role_get(id)
    def role_delete(self,id):
        with self._connect() as c:
            users=c.execute("SELECT COUNT(*) n FROM team_users WHERE role_id=?",(int(id),)).fetchone()["n"]
            if users:return {"ok":False,"error":"Role possui usuários vinculados."}
            c.execute("DELETE FROM team_collection_grants WHERE role_id=?",(int(id),))
            c.execute("DELETE FROM team_track_grants WHERE role_id=?",(int(id),))
            cur=c.execute("DELETE FROM team_roles WHERE id=?",(int(id),))
        return {"ok":cur.rowcount>0,"id":int(id)}

    def _hash_password(self,password,salt=None):
        salt=salt or os.urandom(16)
        if isinstance(salt,str):salt=bytes.fromhex(salt)
        digest=hashlib.pbkdf2_hmac("sha256",str(password).encode("utf-8"),salt,180000)
        return digest.hex(),salt.hex()

    def user_create(self,username,display_name,role_id=None,password=None,notes="",status="active"):
        now=self._now();ph=None;salt=None
        if password:ph,salt=self._hash_password(password)
        try:
            with self._connect() as c:
                cur=c.execute(
                    """INSERT INTO team_users(username,display_name,role_id,status,password_hash,password_salt,
                       notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (str(username).lower().strip(),str(display_name),int(role_id) if role_id else None,
                     str(status),ph,salt,str(notes),now,now)
                )
            return self.user_get(cur.lastrowid)
        except sqlite3.IntegrityError:return {"ok":False,"error":"Usuário já existe."}

    def user_get(self,id):
        with self._connect() as c:
            r=c.execute(
                """SELECT u.id,u.username,u.display_name,u.role_id,u.status,u.notes,u.created_at,u.updated_at,
                          u.last_login,r.name role_name
                   FROM team_users u LEFT JOIN team_roles r ON r.id=u.role_id WHERE u.id=?""",
                (int(id),)
            ).fetchone()
        return {"ok":bool(r),"data":dict(r) if r else None,"error":None if r else "Usuário não encontrado."}

    def user_by_username(self,username,include_secret=False):
        with self._connect() as c:
            r=c.execute(
                """SELECT u.*,r.name role_name FROM team_users u
                   LEFT JOIN team_roles r ON r.id=u.role_id WHERE u.username=?""",
                (str(username).lower().strip(),)
            ).fetchone()
        if not r:return None
        d=dict(r)
        if not include_secret:
            d.pop("password_hash",None);d.pop("password_salt",None)
        return d

    def user_list(self,status=None,role_id=None,limit=500):
        sql="""SELECT u.id,u.username,u.display_name,u.role_id,u.status,u.notes,u.created_at,
                      u.updated_at,u.last_login,r.name role_name
               FROM team_users u LEFT JOIN team_roles r ON r.id=u.role_id WHERE 1=1""";args=[]
        if status:sql+=" AND u.status=?";args.append(str(status))
        if role_id is not None:sql+=" AND u.role_id=?";args.append(int(role_id))
        sql+=" ORDER BY u.display_name LIMIT ?";args.append(int(limit))
        with self._connect() as c:rows=c.execute(sql,args).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def user_update(self,id,**fields):
        sets=[];args=[]
        for k in ("username","display_name","role_id","status","notes"):
            if k in fields and fields[k] is not None:
                v=fields[k]
                if k=="username":v=str(v).lower().strip()
                if k=="role_id" and v!="":v=int(v) if v else None
                sets.append(f"{k}=?");args.append(v)
        if not sets:return self.user_get(id)
        sets.append("updated_at=?");args.append(self._now());args.append(int(id))
        with self._connect() as c:c.execute(f"UPDATE team_users SET {','.join(sets)} WHERE id=?",args)
        return self.user_get(id)

    def user_enable(self,id):return self.user_update(id,status="active")
    def user_disable(self,id):return self.user_update(id,status="disabled")
    def user_delete(self,id):
        with self._connect() as c:cur=c.execute("DELETE FROM team_users WHERE id=?",(int(id),))
        return {"ok":cur.rowcount>0,"id":int(id)}

    def password_set(self,user_id,password):
        digest,salt=self._hash_password(password)
        with self._connect() as c:
            cur=c.execute(
                "UPDATE team_users SET password_hash=?,password_salt=?,updated_at=? WHERE id=?",
                (digest,salt,self._now(),int(user_id))
            )
        return {"ok":cur.rowcount>0,"user_id":int(user_id)}

    def password_clear(self,user_id):
        with self._connect() as c:
            cur=c.execute(
                "UPDATE team_users SET password_hash=NULL,password_salt=NULL,updated_at=? WHERE id=?",
                (self._now(),int(user_id))
            )
        return {"ok":cur.rowcount>0,"user_id":int(user_id)}

    def authenticate(self,username,password):
        user=self.user_by_username(username,include_secret=True)
        if not user or user.get("status")!="active" or not user.get("password_hash"):
            return {"ok":False,"error":"Credenciais inválidas."}
        digest,_=self._hash_password(password,user["password_salt"])
        if not hmac.compare_digest(digest,user["password_hash"]):
            return {"ok":False,"error":"Credenciais inválidas."}
        with self._connect() as c:c.execute("UPDATE team_users SET last_login=? WHERE id=?",(self._now(),user["id"]))
        safe=self.user_get(user["id"])["data"]
        return {"ok":True,"user":safe}

    def collection_grant_set(self,role_id,collection,access_level="read"):
        with self._connect() as c:
            c.execute(
                """INSERT INTO team_collection_grants(role_id,collection,access_level) VALUES(?,?,?)
                   ON CONFLICT(role_id,collection) DO UPDATE SET access_level=excluded.access_level""",
                (int(role_id),str(collection),str(access_level))
            )
        return {"ok":True,"role_id":int(role_id),"collection":str(collection),"access_level":str(access_level)}

    def collection_grant_list(self,role_id):
        with self._connect() as c:rows=c.execute("SELECT * FROM team_collection_grants WHERE role_id=? ORDER BY collection",(int(role_id),)).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def collection_grant_remove(self,role_id,collection):
        with self._connect() as c:cur=c.execute("DELETE FROM team_collection_grants WHERE role_id=? AND collection=?",(int(role_id),str(collection)))
        return {"ok":cur.rowcount>0}

    def track_grant_set(self,role_id,track_id,access_level="read"):
        with self._connect() as c:
            c.execute(
                """INSERT INTO team_track_grants(role_id,track_id,access_level) VALUES(?,?,?)
                   ON CONFLICT(role_id,track_id) DO UPDATE SET access_level=excluded.access_level""",
                (int(role_id),int(track_id),str(access_level))
            )
        return {"ok":True,"role_id":int(role_id),"track_id":int(track_id),"access_level":str(access_level)}

    def track_grant_list(self,role_id):
        with self._connect() as c:rows=c.execute("SELECT * FROM team_track_grants WHERE role_id=? ORDER BY track_id",(int(role_id),)).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def track_grant_remove(self,role_id,track_id):
        with self._connect() as c:cur=c.execute("DELETE FROM team_track_grants WHERE role_id=? AND track_id=?",(int(role_id),int(track_id)))
        return {"ok":cur.rowcount>0}

    def feedback_add(self,user_id=None,rating=None,category="",question="",answer="",comment="",metadata=None):
        with self._connect() as c:
            cur=c.execute(
                """INSERT INTO team_feedback(user_id,created_at,rating,category,question,answer,comment,status,metadata_json)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (int(user_id) if user_id else None,self._now(),int(rating) if rating is not None else None,
                 str(category),str(question),str(answer),str(comment),"open",
                 json.dumps(metadata or {},ensure_ascii=False))
            )
        return self.feedback_get(cur.lastrowid)

    def feedback_get(self,id):
        with self._connect() as c:r=c.execute("SELECT * FROM team_feedback WHERE id=?",(int(id),)).fetchone()
        if not r:return {"ok":False,"error":"Feedback não encontrado."}
        d=dict(r)
        try:d["metadata"]=json.loads(d.pop("metadata_json") or "{}")
        except Exception:d["metadata"]={}
        return {"ok":True,"data":d}

    def feedback_list(self,status=None,rating=None,limit=300):
        sql="SELECT * FROM team_feedback WHERE 1=1";args=[]
        if status:sql+=" AND status=?";args.append(str(status))
        if rating is not None:sql+=" AND rating=?";args.append(int(rating))
        sql+=" ORDER BY id DESC LIMIT ?";args.append(int(limit))
        with self._connect() as c:rows=c.execute(sql,args).fetchall()
        items=[]
        for r in rows:
            d=dict(r)
            try:d["metadata"]=json.loads(d.pop("metadata_json") or "{}")
            except Exception:d["metadata"]={}
            items.append(d)
        return {"ok":True,"items":items,"count":len(items)}

    def feedback_resolve(self,id,status="resolved"):
        with self._connect() as c:cur=c.execute("UPDATE team_feedback SET status=? WHERE id=?",(str(status),int(id)))
        return {"ok":cur.rowcount>0,"id":int(id),"status":str(status)}

    def feedback_stats(self):
        with self._connect() as c:
            total=c.execute("SELECT COUNT(*) n FROM team_feedback").fetchone()["n"]
            avg=c.execute("SELECT AVG(rating) v FROM team_feedback WHERE rating IS NOT NULL").fetchone()["v"]
            rows=c.execute("SELECT rating,COUNT(*) n FROM team_feedback WHERE rating IS NOT NULL GROUP BY rating").fetchall()
        return {"ok":True,"feedback":total,"average_rating":round(avg,2) if avg is not None else None,
                "ratings":{str(r["rating"]):r["n"] for r in rows}}

    def gap_add(self,question,category="",source="team"):
        q=str(question).strip()
        existing_id=None
        created_id=None
        with self._connect() as c:
            r=c.execute("SELECT id,occurrences FROM team_gaps WHERE lower(question)=lower(?) AND status='open'",(q,)).fetchone()
            if r:
                existing_id=int(r["id"])
                c.execute("UPDATE team_gaps SET occurrences=occurrences+1 WHERE id=?",(existing_id,))
            else:
                cur=c.execute(
                    "INSERT INTO team_gaps(created_at,question,category,source,status) VALUES(?,?,?,?,?)",
                    (self._now(),q,str(category),str(source),"open")
                )
                created_id=int(cur.lastrowid)
        return self.gap_get(existing_id if existing_id is not None else created_id)

    def gap_get(self,id):return self._get("team_gaps",id)
    def gap_list(self,status=None,limit=300):
        sql="SELECT * FROM team_gaps";args=[]
        if status:sql+=" WHERE status=?";args.append(str(status))
        sql+=" ORDER BY occurrences DESC,id DESC LIMIT ?";args.append(int(limit))
        with self._connect() as c:rows=c.execute(sql,args).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def gap_search(self,query,limit=100):
        q=f"%{str(query).strip()}%"
        with self._connect() as c:rows=c.execute(
            "SELECT * FROM team_gaps WHERE question LIKE ? OR category LIKE ? ORDER BY occurrences DESC LIMIT ?",
            (q,q,int(limit))
        ).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def gap_resolve(self,id,resolution=""):
        with self._connect() as c:
            cur=c.execute(
                "UPDATE team_gaps SET status='resolved',resolution=?,resolved_at=? WHERE id=?",
                (str(resolution),self._now(),int(id))
            )
        return {"ok":cur.rowcount>0,"id":int(id)}

    def gap_reopen(self,id):
        with self._connect() as c:cur=c.execute(
            "UPDATE team_gaps SET status='open',resolved_at=NULL WHERE id=?",(int(id),)
        )
        return {"ok":cur.rowcount>0,"id":int(id)}

    def gap_stats(self):
        with self._connect() as c:
            total=c.execute("SELECT COUNT(*) n FROM team_gaps").fetchone()["n"]
            open_=c.execute("SELECT COUNT(*) n FROM team_gaps WHERE status='open'").fetchone()["n"]
            occurrences=c.execute("SELECT COALESCE(SUM(occurrences),0) n FROM team_gaps WHERE status='open'").fetchone()["n"]
        return {"ok":True,"gaps":total,"open":open_,"open_occurrences":occurrences}

    def ask_log_add(self,user_id,question,answer="",sources=None,ok=True,latency_ms=None,error=None):
        with self._connect() as c:
            cur=c.execute(
                """INSERT INTO team_ask_log(user_id,created_at,question,answer,sources_json,ok,latency_ms,error)
                   VALUES(?,?,?,?,?,?,?,?)""",
                (int(user_id) if user_id else None,self._now(),str(question),str(answer),
                 json.dumps(sources or [],ensure_ascii=False,default=str),1 if ok else 0,
                 float(latency_ms) if latency_ms is not None else None,str(error)[:2000] if error else None)
            )
        return {"ok":True,"id":int(cur.lastrowid)}

    def ask_log_list(self,user_id=None,ok=None,limit=300):
        sql="SELECT * FROM team_ask_log WHERE 1=1";args=[]
        if user_id is not None:sql+=" AND user_id=?";args.append(int(user_id))
        if ok is not None:sql+=" AND ok=?";args.append(1 if ok else 0)
        sql+=" ORDER BY id DESC LIMIT ?";args.append(int(limit))
        with self._connect() as c:rows=c.execute(sql,args).fetchall()
        items=[]
        for r in rows:
            d=dict(r)
            try:d["sources"]=json.loads(d.pop("sources_json") or "[]")
            except Exception:d["sources"]=[]
            items.append(d)
        return {"ok":True,"items":items,"count":len(items)}

    def setting_get(self,key=None):
        with self._connect() as c:
            if key:
                r=c.execute("SELECT * FROM team_settings WHERE key=?",(str(key),)).fetchone()
                return {"ok":bool(r),"data":dict(r) if r else None}
            rows=c.execute("SELECT * FROM team_settings ORDER BY key").fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def setting_set(self,key,value):
        with self._connect() as c:
            c.execute(
                """INSERT INTO team_settings(key,value,updated_at) VALUES(?,?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
                (str(key),str(value),self._now())
            )
        return self.setting_get(key)

    def stats(self):
        with self._connect() as c:
            users=c.execute("SELECT COUNT(*) n FROM team_users").fetchone()["n"]
            active=c.execute("SELECT COUNT(*) n FROM team_users WHERE status='active'").fetchone()["n"]
            roles=c.execute("SELECT COUNT(*) n FROM team_roles").fetchone()["n"]
            questions=c.execute("SELECT COUNT(*) n FROM team_ask_log").fetchone()["n"]
        fs=self.feedback_stats();gs=self.gap_stats()
        return {"ok":True,"users":users,"active_users":active,"roles":roles,"questions":questions,
                "feedback":fs.get("feedback",0),"average_rating":fs.get("average_rating"),
                "knowledge_gaps_open":gs.get("open",0)}

    def execute(self,operation,**params):
        mapping={
          "role_create":self.role_create,"role_get":self.role_get,"role_list":self.role_list,
          "role_update":self.role_update,"role_delete":self.role_delete,
          "user_create":self.user_create,"user_get":self.user_get,"user_list":self.user_list,
          "user_update":self.user_update,"user_enable":self.user_enable,"user_disable":self.user_disable,
          "user_delete":self.user_delete,"password_set":self.password_set,"password_clear":self.password_clear,
          "authenticate":self.authenticate,
          "collection_grant_set":self.collection_grant_set,"collection_grant_list":self.collection_grant_list,
          "collection_grant_remove":self.collection_grant_remove,
          "track_grant_set":self.track_grant_set,"track_grant_list":self.track_grant_list,
          "track_grant_remove":self.track_grant_remove,
          "feedback_add":self.feedback_add,"feedback_get":self.feedback_get,"feedback_list":self.feedback_list,
          "feedback_resolve":self.feedback_resolve,"feedback_stats":self.feedback_stats,
          "gap_add":self.gap_add,"gap_get":self.gap_get,"gap_list":self.gap_list,
          "gap_search":self.gap_search,"gap_resolve":self.gap_resolve,"gap_reopen":self.gap_reopen,
          "gap_stats":self.gap_stats,"ask_log_add":self.ask_log_add,"ask_log_list":self.ask_log_list,
          "setting_get":self.setting_get,"setting_set":self.setting_set,"stats":self.stats,
        }
        fn=mapping.get(operation)
        if not fn:return {"ok":False,"error":f"Operação Team Assistant desconhecida: {operation}"}
        return fn(**params)
