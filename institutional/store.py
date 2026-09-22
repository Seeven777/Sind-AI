import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path


class InstitutionalStore:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS organization (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                department TEXT DEFAULT '',
                description TEXT DEFAULT '',
                responsibilities TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS glossary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                term TEXT NOT NULL UNIQUE,
                definition TEXT NOT NULL,
                aliases TEXT DEFAULT '',
                source TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS policies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                category TEXT DEFAULT '',
                source TEXT DEFAULT '',
                version TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS style_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                rule TEXT NOT NULL,
                channel TEXT DEFAULT 'general',
                priority INTEGER NOT NULL DEFAULT 50,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT DEFAULT '',
                source_type TEXT DEFAULT 'internal',
                authority INTEGER NOT NULL DEFAULT 50,
                collection TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                owner_role TEXT DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                workspace_path TEXT DEFAULT '',
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_policies_category ON policies(category);
            CREATE INDEX IF NOT EXISTS idx_sources_collection ON sources(collection);
            CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status);
            """)

    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def _rows(self, rows):
        out=[]
        for r in rows:
            d=dict(r)
            for key in ("metadata_json",):
                if key in d:
                    raw=d.pop(key)
                    try: d["metadata"]=json.loads(raw or "{}")
                    except Exception: d["metadata"]={}
            out.append(d)
        return out

    def _get_by_id(self, table, item_id):
        with self._connect() as conn:
            row=conn.execute(f"SELECT * FROM {table} WHERE id=?", (int(item_id),)).fetchone()
        return {"ok": bool(row), "data": self._rows([row])[0] if row else None, "error": None if row else "Registro não encontrado."}

    def _list(self, table, status=None, limit=200, order="id DESC"):
        sql=f"SELECT * FROM {table}"
        args=[]
        if status:
            sql += " WHERE status=?"; args.append(status)
        sql += f" ORDER BY {order} LIMIT ?"; args.append(int(limit))
        with self._connect() as conn:
            rows=conn.execute(sql,args).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def _search(self, table, fields, query, limit=100):
        q=f"%{str(query).strip()}%"
        where=" OR ".join([f"{f} LIKE ?" for f in fields])
        with self._connect() as conn:
            rows=conn.execute(f"SELECT * FROM {table} WHERE {where} ORDER BY id DESC LIMIT ?", [q]*len(fields)+[int(limit)]).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def execute(self, operation, **p):
        now=self._now()
        try:
            if operation == "profile_get":
                with self._connect() as conn:
                    rows=conn.execute("SELECT key,value,updated_at FROM organization ORDER BY key").fetchall()
                data={r["key"]:r["value"] for r in rows}
                return {"ok":True,"data":data,"count":len(data)}
            if operation == "profile_set":
                key=str(p["key"]).strip(); value=str(p.get("value", "")).strip()
                with self._connect() as conn:
                    conn.execute("INSERT INTO organization(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", (key,value,now))
                return {"ok":True,"key":key,"value":value}
            if operation == "profile_delete":
                with self._connect() as conn: cur=conn.execute("DELETE FROM organization WHERE key=?", (str(p["key"]),))
                return {"ok":True,"removed":cur.rowcount}
            if operation == "profile_export":
                data=self.execute("profile_get")["data"]
                out=Path(p["path"]).expanduser().resolve(); out.parent.mkdir(parents=True,exist_ok=True)
                out.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8")
                return {"ok":True,"path":str(out),"fields":len(data)}

            if operation == "department_create":
                with self._connect() as conn:
                    cur=conn.execute("INSERT INTO departments(name,description,status,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?)", (p["name"],p.get("description",""),p.get("status","active"),json.dumps(p.get("metadata",{}),ensure_ascii=False),now,now))
                return {"ok":True,"id":cur.lastrowid}
            if operation == "department_list": return self._list("departments",p.get("status"),p.get("limit",200),"name")
            if operation == "department_get": return self._get_by_id("departments",p["id"])
            if operation == "department_search": return self._search("departments",["name","description"],p["query"],p.get("limit",100))
            if operation == "department_update":
                fields=[]; args=[]
                for k in ("name","description","status"):
                    if k in p and p[k] is not None: fields.append(f"{k}=?"); args.append(p[k])
                if "metadata" in p: fields.append("metadata_json=?"); args.append(json.dumps(p["metadata"],ensure_ascii=False))
                fields.append("updated_at=?"); args.append(now); args.append(int(p["id"]))
                with self._connect() as conn: cur=conn.execute(f"UPDATE departments SET {', '.join(fields)} WHERE id=?",args)
                return {"ok":True,"updated":cur.rowcount}
            if operation == "department_archive":
                return self.execute("department_update",id=p["id"],status="archived")

            if operation == "role_create":
                with self._connect() as conn:
                    cur=conn.execute("INSERT INTO roles(name,department,description,responsibilities,status,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (p["name"],p.get("department",""),p.get("description",""),p.get("responsibilities",""),p.get("status","active"),json.dumps(p.get("metadata",{}),ensure_ascii=False),now,now))
                return {"ok":True,"id":cur.lastrowid}
            if operation == "role_list": return self._list("roles",p.get("status"),p.get("limit",200),"name")
            if operation == "role_get": return self._get_by_id("roles",p["id"])
            if operation == "role_search": return self._search("roles",["name","department","description","responsibilities"],p["query"],p.get("limit",100))
            if operation == "role_update":
                fields=[]; args=[]
                for k in ("name","department","description","responsibilities","status"):
                    if k in p and p[k] is not None: fields.append(f"{k}=?"); args.append(p[k])
                if "metadata" in p: fields.append("metadata_json=?"); args.append(json.dumps(p["metadata"],ensure_ascii=False))
                fields.append("updated_at=?"); args.append(now); args.append(int(p["id"]))
                with self._connect() as conn: cur=conn.execute(f"UPDATE roles SET {', '.join(fields)} WHERE id=?",args)
                return {"ok":True,"updated":cur.rowcount}
            if operation == "role_archive": return self.execute("role_update",id=p["id"],status="archived")

            if operation == "glossary_create":
                with self._connect() as conn:
                    cur=conn.execute("INSERT INTO glossary(term,definition,aliases,source,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",(p["term"],p["definition"],p.get("aliases",""),p.get("source",""),p.get("status","active"),now,now))
                return {"ok":True,"id":cur.lastrowid}
            if operation == "glossary_list": return self._list("glossary",p.get("status"),p.get("limit",300),"term")
            if operation == "glossary_search": return self._search("glossary",["term","definition","aliases","source"],p["query"],p.get("limit",100))
            if operation == "glossary_get": return self._get_by_id("glossary",p["id"])
            if operation == "glossary_update":
                fields=[];args=[]
                for k in ("term","definition","aliases","source","status"):
                    if k in p and p[k] is not None: fields.append(f"{k}=?"); args.append(p[k])
                fields.append("updated_at=?");args.append(now);args.append(int(p["id"]))
                with self._connect() as conn: cur=conn.execute(f"UPDATE glossary SET {', '.join(fields)} WHERE id=?",args)
                return {"ok":True,"updated":cur.rowcount}
            if operation == "glossary_remove":
                with self._connect() as conn: cur=conn.execute("DELETE FROM glossary WHERE id=?",(int(p["id"]),))
                return {"ok":True,"removed":cur.rowcount}

            if operation == "policy_create":
                with self._connect() as conn:
                    cur=conn.execute("INSERT INTO policies(title,body,category,source,version,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(p["title"],p["body"],p.get("category",""),p.get("source",""),p.get("version",""),p.get("status","active"),now,now))
                return {"ok":True,"id":cur.lastrowid}
            if operation == "policy_list": return self._list("policies",p.get("status"),p.get("limit",200))
            if operation == "policy_get": return self._get_by_id("policies",p["id"])
            if operation == "policy_search": return self._search("policies",["title","body","category","source","version"],p["query"],p.get("limit",100))
            if operation == "policy_update":
                fields=[];args=[]
                for k in ("title","body","category","source","version","status"):
                    if k in p and p[k] is not None: fields.append(f"{k}=?");args.append(p[k])
                fields.append("updated_at=?");args.append(now);args.append(int(p["id"]))
                with self._connect() as conn: cur=conn.execute(f"UPDATE policies SET {', '.join(fields)} WHERE id=?",args)
                return {"ok":True,"updated":cur.rowcount}
            if operation == "policy_archive": return self.execute("policy_update",id=p["id"],status="archived")

            if operation == "style_create":
                with self._connect() as conn:
                    cur=conn.execute("INSERT INTO style_rules(name,rule,channel,priority,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",(p["name"],p["rule"],p.get("channel","general"),int(p.get("priority",50)),p.get("status","active"),now,now))
                return {"ok":True,"id":cur.lastrowid}
            if operation == "style_list": return self._list("style_rules",p.get("status"),p.get("limit",300),"priority DESC, name")
            if operation == "style_search": return self._search("style_rules",["name","rule","channel"],p["query"],p.get("limit",100))
            if operation == "style_get": return self._get_by_id("style_rules",p["id"])
            if operation == "style_update":
                fields=[];args=[]
                for k in ("name","rule","channel","priority","status"):
                    if k in p and p[k] is not None: fields.append(f"{k}=?");args.append(p[k])
                fields.append("updated_at=?");args.append(now);args.append(int(p["id"]))
                with self._connect() as conn: cur=conn.execute(f"UPDATE style_rules SET {', '.join(fields)} WHERE id=?",args)
                return {"ok":True,"updated":cur.rowcount}
            if operation == "style_remove":
                with self._connect() as conn: cur=conn.execute("DELETE FROM style_rules WHERE id=?",(int(p["id"]),))
                return {"ok":True,"removed":cur.rowcount}

            if operation == "source_create":
                with self._connect() as conn:
                    cur=conn.execute("INSERT INTO sources(name,url,source_type,authority,collection,notes,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",(p["name"],p.get("url",""),p.get("source_type","internal"),int(p.get("authority",50)),p.get("collection",""),p.get("notes",""),p.get("status","active"),now,now))
                return {"ok":True,"id":cur.lastrowid}
            if operation == "source_list": return self._list("sources",p.get("status"),p.get("limit",300),"authority DESC, name")
            if operation == "source_get": return self._get_by_id("sources",p["id"])
            if operation == "source_search": return self._search("sources",["name","url","source_type","collection","notes"],p["query"],p.get("limit",100))
            if operation == "source_update":
                fields=[];args=[]
                for k in ("name","url","source_type","authority","collection","notes","status"):
                    if k in p and p[k] is not None: fields.append(f"{k}=?");args.append(p[k])
                fields.append("updated_at=?");args.append(now);args.append(int(p["id"]))
                with self._connect() as conn: cur=conn.execute(f"UPDATE sources SET {', '.join(fields)} WHERE id=?",args)
                return {"ok":True,"updated":cur.rowcount}
            if operation == "source_archive": return self.execute("source_update",id=p["id"],status="archived")
            if operation == "source_authority":
                data=self._get_by_id("sources",p["id"])
                return {"ok":data["ok"],"authority":(data.get("data") or {}).get("authority"),"source":data.get("data")}

            if operation == "project_create":
                with self._connect() as conn:
                    cur=conn.execute("INSERT INTO projects(name,description,owner_role,status,workspace_path,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(p["name"],p.get("description",""),p.get("owner_role",""),p.get("status","active"),p.get("workspace_path",""),json.dumps(p.get("metadata",{}),ensure_ascii=False),now,now))
                return {"ok":True,"id":cur.lastrowid}
            if operation == "project_list": return self._list("projects",p.get("status"),p.get("limit",200),"updated_at DESC")
            if operation == "project_get": return self._get_by_id("projects",p["id"])
            if operation == "project_search": return self._search("projects",["name","description","owner_role","workspace_path"],p["query"],p.get("limit",100))
            if operation == "project_update":
                fields=[];args=[]
                for k in ("name","description","owner_role","status","workspace_path"):
                    if k in p and p[k] is not None: fields.append(f"{k}=?");args.append(p[k])
                if "metadata" in p: fields.append("metadata_json=?");args.append(json.dumps(p["metadata"],ensure_ascii=False))
                fields.append("updated_at=?");args.append(now);args.append(int(p["id"]))
                with self._connect() as conn: cur=conn.execute(f"UPDATE projects SET {', '.join(fields)} WHERE id=?",args)
                return {"ok":True,"updated":cur.rowcount}
            if operation == "project_archive": return self.execute("project_update",id=p["id"],status="archived")

            if operation == "context_bundle":
                profile=self.execute("profile_get").get("data",{})
                glossary=self.execute("glossary_list",status="active",limit=p.get("glossary_limit",40)).get("items",[])
                policies=self.execute("policy_list",status="active",limit=p.get("policy_limit",20)).get("items",[])
                styles=self.execute("style_list",status="active",limit=p.get("style_limit",30)).get("items",[])
                roles=self.execute("role_list",status="active",limit=100).get("items",[])
                return {"ok":True,"profile":profile,"glossary":glossary,"policies":policies,"style_rules":styles,"roles":roles}

            if operation == "stats":
                with self._connect() as conn:
                    tables=["departments","roles","glossary","policies","style_rules","sources","projects"]
                    counts={t:conn.execute(f"SELECT COUNT(*) n FROM {t} WHERE status!='archived'").fetchone()["n"] for t in tables}
                    profile=conn.execute("SELECT COUNT(*) n FROM organization").fetchone()["n"]
                return {"ok":True,"profile_fields":profile,**counts}

            return {"ok":False,"error":f"Operação institucional desconhecida: {operation}"}
        except sqlite3.IntegrityError as exc:
            return {"ok":False,"error":f"Conflito de dados: {exc}"}
        except Exception as exc:
            return {"ok":False,"error":str(exc)}
