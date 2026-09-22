import json
import sqlite3
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import requests


WRITE_METHODS={"POST","PUT","PATCH","DELETE"}


class ConnectorGateway:
    """
    Gateway genérico para APIs HTTPS autorizadas.

    Segredos ficam no keyring do sistema, nunca no SQLite.
    """

    def __init__(self,db_path,user_agent="JarvisSindPet/0.9"):
        self.db_path=Path(db_path);self.db_path.parent.mkdir(parents=True,exist_ok=True)
        self.user_agent=user_agent
        self.session=requests.Session();self.session.headers.update({"User-Agent":user_agent})
        self._init_db()

    def _connect(self):
        c=sqlite3.connect(self.db_path,timeout=20);c.row_factory=sqlite3.Row;return c
    def _now(self):return datetime.now().isoformat(timespec="seconds")

    def _init_db(self):
        with self._connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS connector_profiles(
              id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,
              base_url TEXT NOT NULL,auth_type TEXT NOT NULL DEFAULT 'none',
              auth_config_json TEXT NOT NULL DEFAULT '{}',
              default_headers_json TEXT NOT NULL DEFAULT '{}',
              status TEXT NOT NULL DEFAULT 'disabled',description TEXT DEFAULT '',
              created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS connector_endpoints(
              id INTEGER PRIMARY KEY AUTOINCREMENT,connector_id INTEGER NOT NULL,
              name TEXT NOT NULL,method TEXT NOT NULL,path TEXT NOT NULL,
              params_json TEXT NOT NULL DEFAULT '{}',headers_json TEXT NOT NULL DEFAULT '{}',
              body_template_json TEXT NOT NULL DEFAULT '{}',
              risk TEXT NOT NULL DEFAULT 'read',description TEXT DEFAULT '',
              status TEXT NOT NULL DEFAULT 'enabled',created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
              UNIQUE(connector_id,name),
              FOREIGN KEY(connector_id) REFERENCES connector_profiles(id));
            CREATE TABLE IF NOT EXISTS connector_history(
              id INTEGER PRIMARY KEY AUTOINCREMENT,connector_id INTEGER,
              endpoint_id INTEGER,created_at TEXT NOT NULL,method TEXT NOT NULL,
              url TEXT NOT NULL,status_code INTEGER,ok INTEGER,error TEXT,
              elapsed_ms REAL,response_preview TEXT DEFAULT '');
            CREATE INDEX IF NOT EXISTS idx_connector_history ON connector_history(connector_id,id DESC);
            """)

    def _json(self,raw,default=None):
        try:return json.loads(raw or "{}")
        except Exception:return {} if default is None else default

    def _profile_row(self,row):
        if not row:return None
        d=dict(row);d["auth_config"]=self._json(d.pop("auth_config_json"));d["default_headers"]=self._json(d.pop("default_headers_json"));return d
    def _endpoint_row(self,row):
        if not row:return None
        d=dict(row)
        d["params"]=self._json(d.pop("params_json"));d["headers"]=self._json(d.pop("headers_json"));d["body_template"]=self._json(d.pop("body_template_json"))
        return d

    def _keyring(self):
        try:import keyring;return keyring
        except Exception as exc:raise RuntimeError("Pacote keyring não disponível.") from exc
    def _secret_user(self,connector_id,key):return f"{int(connector_id)}:{str(key)}"

    def secret_set(self,connector_id,key,value):
        self.get(connector_id)  # validates
        self._keyring().set_password("JarvisConnector",self._secret_user(connector_id,key),str(value))
        return {"ok":True,"connector_id":int(connector_id),"key":str(key)}

    def secret_status(self,connector_id,key=None):
        keys=[key] if key else ["token","password","api_key","client_secret"]
        kr=self._keyring();items={}
        for k in keys:items[str(k)]=bool(kr.get_password("JarvisConnector",self._secret_user(connector_id,k)))
        return {"ok":True,"connector_id":int(connector_id),"secrets":items}

    def secret_delete(self,connector_id,key):
        kr=self._keyring()
        try:kr.delete_password("JarvisConnector",self._secret_user(connector_id,key));removed=True
        except Exception:removed=False
        return {"ok":True,"removed":removed,"connector_id":int(connector_id),"key":str(key)}

    def create(self,name,base_url,auth_type="none",auth_config=None,default_headers=None,
               description="",enabled=False):
        base=str(base_url).strip().rstrip("/")+"/"
        if not base.startswith("https://"):
            return {"ok":False,"error":"Connectors externos aceitam apenas HTTPS."}
        now=self._now()
        try:
            with self._connect() as c:
                cur=c.execute(
                    """INSERT INTO connector_profiles(name,base_url,auth_type,auth_config_json,
                       default_headers_json,status,description,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (str(name).strip(),base,str(auth_type).lower(),json.dumps(auth_config or {},ensure_ascii=False),
                     json.dumps(default_headers or {},ensure_ascii=False),"enabled" if enabled else "disabled",
                     str(description),now,now)
                )
            return self.get(cur.lastrowid)
        except sqlite3.IntegrityError:
            return {"ok":False,"error":f"Já existe connector chamado '{name}'."}

    def get(self,connector_id=None,name=None):
        with self._connect() as c:
            if connector_id is not None:r=c.execute("SELECT * FROM connector_profiles WHERE id=?",(int(connector_id),)).fetchone()
            else:r=c.execute("SELECT * FROM connector_profiles WHERE name=?",(str(name),)).fetchone()
        return {"ok":bool(r),"data":self._profile_row(r),"error":None if r else "Connector não encontrado."}

    def list(self,status=None,limit=200):
        sql="SELECT * FROM connector_profiles";args=[]
        if status:sql+=" WHERE status=?";args.append(str(status))
        sql+=" ORDER BY id DESC LIMIT ?";args.append(int(limit))
        with self._connect() as c:rows=c.execute(sql,args).fetchall()
        return {"ok":True,"items":[self._profile_row(r) for r in rows],"count":len(rows)}

    def update(self,connector_id,**fields):
        sets=[];args=[]
        for k in ("name","base_url","auth_type","status","description"):
            if k in fields and fields[k] is not None:
                v=fields[k]
                if k=="base_url":
                    v=str(v).strip().rstrip("/")+"/"
                    if not v.startswith("https://"):return {"ok":False,"error":"Apenas HTTPS."}
                sets.append(f"{k}=?");args.append(v)
        if "auth_config" in fields and fields["auth_config"] is not None:
            sets.append("auth_config_json=?");args.append(json.dumps(fields["auth_config"],ensure_ascii=False))
        if "default_headers" in fields and fields["default_headers"] is not None:
            sets.append("default_headers_json=?");args.append(json.dumps(fields["default_headers"],ensure_ascii=False))
        if not sets:return self.get(connector_id)
        sets.append("updated_at=?");args.append(self._now());args.append(int(connector_id))
        try:
            with self._connect() as c:c.execute(f"UPDATE connector_profiles SET {','.join(sets)} WHERE id=?",args)
        except sqlite3.IntegrityError as exc:return {"ok":False,"error":str(exc)}
        return self.get(connector_id)

    def enable(self,connector_id):return self.update(connector_id,status="enabled")
    def disable(self,connector_id):return self.update(connector_id,status="disabled")

    def delete(self,connector_id):
        eps=self.endpoint_list(connector_id,limit=10000)["items"]
        with self._connect() as c:
            c.execute("DELETE FROM connector_history WHERE connector_id=?",(int(connector_id),))
            c.execute("DELETE FROM connector_endpoints WHERE connector_id=?",(int(connector_id),))
            cur=c.execute("DELETE FROM connector_profiles WHERE id=?",(int(connector_id),))
        for k in ("token","password","api_key","client_secret"):
            try:self.secret_delete(connector_id,k)
            except Exception:pass
        return {"ok":cur.rowcount>0,"id":int(connector_id),"endpoints_removed":len(eps)}

    def endpoint_create(self,connector_id,name,method,path,params=None,headers=None,body_template=None,
                        risk=None,description="",enabled=True):
        profile=self.get(connector_id).get("data")
        if not profile:return {"ok":False,"error":"Connector não encontrado."}
        method=str(method).upper()
        if method not in {"GET","POST","PUT","PATCH","DELETE","HEAD"}:
            return {"ok":False,"error":"Método HTTP não permitido."}
        risk=risk or ("read" if method in {"GET","HEAD"} else "write")
        now=self._now()
        try:
            with self._connect() as c:
                cur=c.execute(
                    """INSERT INTO connector_endpoints(connector_id,name,method,path,params_json,headers_json,
                       body_template_json,risk,description,status,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (int(connector_id),str(name),method,str(path),json.dumps(params or {},ensure_ascii=False),
                     json.dumps(headers or {},ensure_ascii=False),json.dumps(body_template or {},ensure_ascii=False),
                     str(risk),str(description),"enabled" if enabled else "disabled",now,now)
                )
            return self.endpoint_get(cur.lastrowid)
        except sqlite3.IntegrityError:
            return {"ok":False,"error":"Já existe endpoint com esse nome neste connector."}

    def endpoint_get(self,endpoint_id):
        with self._connect() as c:r=c.execute("SELECT * FROM connector_endpoints WHERE id=?",(int(endpoint_id),)).fetchone()
        return {"ok":bool(r),"data":self._endpoint_row(r),"error":None if r else "Endpoint não encontrado."}

    def endpoint_list(self,connector_id=None,status=None,risk=None,limit=500):
        sql="SELECT * FROM connector_endpoints WHERE 1=1";args=[]
        if connector_id is not None:sql+=" AND connector_id=?";args.append(int(connector_id))
        if status:sql+=" AND status=?";args.append(str(status))
        if risk:sql+=" AND risk=?";args.append(str(risk))
        sql+=" ORDER BY id DESC LIMIT ?";args.append(int(limit))
        with self._connect() as c:rows=c.execute(sql,args).fetchall()
        return {"ok":True,"items":[self._endpoint_row(r) for r in rows],"count":len(rows)}

    def endpoint_update(self,endpoint_id,**fields):
        sets=[];args=[]
        for k in ("name","method","path","risk","description","status"):
            if k in fields and fields[k] is not None:sets.append(f"{k}=?");args.append(str(fields[k]).upper() if k=="method" else fields[k])
        for k,col in [("params","params_json"),("headers","headers_json"),("body_template","body_template_json")]:
            if k in fields and fields[k] is not None:sets.append(f"{col}=?");args.append(json.dumps(fields[k],ensure_ascii=False))
        if not sets:return self.endpoint_get(endpoint_id)
        sets.append("updated_at=?");args.append(self._now());args.append(int(endpoint_id))
        with self._connect() as c:c.execute(f"UPDATE connector_endpoints SET {','.join(sets)} WHERE id=?",args)
        return self.endpoint_get(endpoint_id)

    def endpoint_enable(self,endpoint_id):return self.endpoint_update(endpoint_id,status="enabled")
    def endpoint_disable(self,endpoint_id):return self.endpoint_update(endpoint_id,status="disabled")
    def endpoint_delete(self,endpoint_id):
        with self._connect() as c:cur=c.execute("DELETE FROM connector_endpoints WHERE id=?",(int(endpoint_id),))
        return {"ok":cur.rowcount>0,"id":int(endpoint_id)}

    def _render(self,value,params):
        if isinstance(value,str):
            out=value
            for k,v in (params or {}).items():out=out.replace("{{"+str(k)+"}}",str(v))
            return out
        if isinstance(value,dict):return {k:self._render(v,params) for k,v in value.items()}
        if isinstance(value,list):return [self._render(v,params) for v in value]
        return value

    def _auth_headers(self,profile):
        auth_type=profile["auth_type"];cfg=profile["auth_config"];headers={}
        kr=self._keyring()
        if auth_type=="bearer":
            token=kr.get_password("JarvisConnector",self._secret_user(profile["id"],"token"))
            if not token:raise RuntimeError("Bearer token não configurado.")
            headers["Authorization"]="Bearer "+token
        elif auth_type=="api_key_header":
            key=kr.get_password("JarvisConnector",self._secret_user(profile["id"],"api_key"))
            if not key:raise RuntimeError("API key não configurada.")
            headers[str(cfg.get("header","X-API-Key"))]=key
        elif auth_type=="basic":
            # basic is returned separately in execute
            pass
        elif auth_type not in {"none",""}:
            raise RuntimeError(f"auth_type não suportado: {auth_type}")
        return headers

    def preview(self,endpoint_id,params=None):
        ep=self.endpoint_get(endpoint_id).get("data")
        if not ep:return {"ok":False,"error":"Endpoint não encontrado."}
        profile=self.get(ep["connector_id"]).get("data")
        values=dict(params or {})
        url=urljoin(profile["base_url"],self._render(ep["path"],values).lstrip("/"))
        query=self._render(ep["params"],values)
        headers={**profile["default_headers"],**ep["headers"]}
        # Preview must never require or reveal a stored secret.
        auth_type = profile["auth_type"]
        if auth_type == "bearer":
            headers["Authorization"] = "<secret>"
        elif auth_type == "api_key_header":
            headers[str(profile["auth_config"].get("header", "X-API-Key"))] = "<secret>"
        elif auth_type == "basic":
            headers["Authorization"] = "<basic secret>"
        body=self._render(ep["body_template"],values)
        return {"ok":True,"method":ep["method"],"url":url,"query":query,"headers":headers,
                "body":body,"risk":ep["risk"],"connector":profile["name"],"endpoint":ep["name"]}

    def _record(self,connector_id,endpoint_id,method,url,status_code,ok,error,elapsed_ms,preview):
        with self._connect() as c:
            c.execute(
                """INSERT INTO connector_history(connector_id,endpoint_id,created_at,method,url,status_code,
                   ok,error,elapsed_ms,response_preview) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (connector_id,endpoint_id,self._now(),method,url,status_code,1 if ok else 0,
                 str(error)[:2000] if error else None,float(elapsed_ms),str(preview)[:4000])
            )

    def execute_endpoint(self,endpoint_id,params=None,timeout=30):
        import time
        ep=self.endpoint_get(endpoint_id).get("data")
        if not ep:return {"ok":False,"error":"Endpoint não encontrado."}
        if ep["status"]!="enabled":return {"ok":False,"error":"Endpoint desabilitado."}
        profile=self.get(ep["connector_id"]).get("data")
        if not profile:return {"ok":False,"error":"Connector não encontrado."}
        if profile["status"]!="enabled":return {"ok":False,"error":"Connector desabilitado."}
        values=dict(params or {})
        url=urljoin(profile["base_url"],self._render(ep["path"],values).lstrip("/"))
        if not url.startswith("https://"):return {"ok":False,"error":"URL final não HTTPS."}
        query=self._render(ep["params"],values)
        headers={**profile["default_headers"],**ep["headers"],**self._auth_headers(profile)}
        body=self._render(ep["body_template"],values)
        auth=None
        if profile["auth_type"]=="basic":
            user=str(profile["auth_config"].get("username",""))
            password=self._keyring().get_password("JarvisConnector",self._secret_user(profile["id"],"password"))
            if not password:return {"ok":False,"error":"Senha Basic Auth não configurada."}
            auth=(user,password)
        started=time.monotonic()
        try:
            r=self.session.request(ep["method"],url,params=query if query else None,
                                   json=body if body and ep["method"] in WRITE_METHODS else None,
                                   headers=headers,auth=auth,timeout=int(timeout))
            elapsed=(time.monotonic()-started)*1000
            ctype=(r.headers.get("content-type") or "").lower()
            try:data=r.json() if "json" in ctype else r.text[:20000]
            except Exception:data=r.text[:20000]
            result={"ok":r.ok,"status":r.status_code,"data":data,"url":r.url,
                    "elapsed_ms":round(elapsed,1),"risk":ep["risk"],"endpoint":ep["name"],
                    "connector":profile["name"]}
            self._record(profile["id"],ep["id"],ep["method"],r.url,r.status_code,r.ok,
                         None if r.ok else str(data)[:1000],elapsed,str(data)[:1000])
            return result
        except Exception as exc:
            elapsed=(time.monotonic()-started)*1000
            self._record(profile["id"],ep["id"],ep["method"],url,None,False,str(exc),elapsed,"")
            return {"ok":False,"error":str(exc),"url":url,"risk":ep["risk"],
                    "endpoint":ep["name"],"connector":profile["name"]}

    def test(self,connector_id,path="",timeout=15):
        profile=self.get(connector_id).get("data")
        if not profile:return {"ok":False,"error":"Connector não encontrado."}
        if profile["status"]!="enabled":return {"ok":False,"error":"Connector desabilitado."}
        url=urljoin(profile["base_url"],str(path).lstrip("/"))
        try:
            headers={**profile["default_headers"],**self._auth_headers(profile)}
            auth=None
            if profile["auth_type"]=="basic":
                user=str(profile["auth_config"].get("username",""))
                pwd=self._keyring().get_password("JarvisConnector",self._secret_user(profile["id"],"password"))
                if pwd:auth=(user,pwd)
            r=self.session.get(url,headers=headers,auth=auth,timeout=int(timeout))
            return {"ok":r.ok,"status":r.status_code,"url":r.url}
        except Exception as exc:return {"ok":False,"error":str(exc)}

    def history(self,connector_id=None,endpoint_id=None,ok=None,limit=200):
        sql="SELECT * FROM connector_history WHERE 1=1";args=[]
        if connector_id is not None:sql+=" AND connector_id=?";args.append(int(connector_id))
        if endpoint_id is not None:sql+=" AND endpoint_id=?";args.append(int(endpoint_id))
        if ok is not None:sql+=" AND ok=?";args.append(1 if ok else 0)
        sql+=" ORDER BY id DESC LIMIT ?";args.append(int(limit))
        with self._connect() as c:rows=c.execute(sql,args).fetchall()
        return {"ok":True,"items":[dict(r) for r in rows],"count":len(rows)}

    def clear_history(self,connector_id=None):
        with self._connect() as c:
            if connector_id is None:cur=c.execute("DELETE FROM connector_history")
            else:cur=c.execute("DELETE FROM connector_history WHERE connector_id=?",(int(connector_id),))
        return {"ok":True,"removed":cur.rowcount}

    def stats(self):
        with self._connect() as c:
            profiles=c.execute("SELECT COUNT(*) n FROM connector_profiles").fetchone()["n"]
            enabled=c.execute("SELECT COUNT(*) n FROM connector_profiles WHERE status='enabled'").fetchone()["n"]
            endpoints=c.execute("SELECT COUNT(*) n FROM connector_endpoints").fetchone()["n"]
            writes=c.execute("SELECT COUNT(*) n FROM connector_endpoints WHERE risk!='read'").fetchone()["n"]
            calls=c.execute("SELECT COUNT(*) n FROM connector_history").fetchone()["n"]
        return {"ok":True,"connectors":profiles,"enabled":enabled,"endpoints":endpoints,
                "write_endpoints":writes,"calls":calls}

    def export(self,path):
        out=Path(path).expanduser().resolve();out.parent.mkdir(parents=True,exist_ok=True)
        profiles=self.list(limit=10000)["items"]
        payload=[]
        for p in profiles:
            payload.append({"profile":p,"endpoints":self.endpoint_list(p["id"],limit=10000)["items"]})
        out.write_text(json.dumps(payload,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
        return {"ok":True,"path":str(out),"connectors":len(payload),"note":"Segredos não são exportados."}

    def execute(self,operation,**params):
        mapping={
          "create":self.create,"get":self.get,"list":self.list,"update":self.update,
          "enable":self.enable,"disable":self.disable,"delete":self.delete,"test":self.test,
          "secret_set":self.secret_set,"secret_status":self.secret_status,"secret_delete":self.secret_delete,
          "endpoint_create":self.endpoint_create,"endpoint_get":self.endpoint_get,
          "endpoint_list":self.endpoint_list,"endpoint_update":self.endpoint_update,
          "endpoint_enable":self.endpoint_enable,"endpoint_disable":self.endpoint_disable,
          "endpoint_delete":self.endpoint_delete,"preview":self.preview,
          "execute_endpoint":self.execute_endpoint,"history":self.history,
          "clear_history":self.clear_history,"stats":self.stats,"export":self.export,
        }
        fn=mapping.get(operation)
        if not fn:return {"ok":False,"error":f"Operação de connector desconhecida: {operation}"}
        return fn(**params)
