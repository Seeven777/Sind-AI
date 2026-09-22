import json
import sqlite3
from datetime import datetime
from pathlib import Path


RISK_RANK={'read':0,'draft':1,'write':2,'publish':3,'admin':4}

class GovernanceEngine:
    def __init__(self, db_path):
        self.db_path=Path(db_path); self.db_path.parent.mkdir(parents=True,exist_ok=True); self._init_db()

    def _connect(self):
        conn=sqlite3.connect(self.db_path); conn.row_factory=sqlite3.Row; return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS connectors(
              id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,
              connector_type TEXT NOT NULL,environment TEXT DEFAULT 'production',
              endpoint TEXT DEFAULT '',status TEXT DEFAULT 'disabled',notes TEXT DEFAULT '',
              created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS permissions(
              id INTEGER PRIMARY KEY AUTOINCREMENT,connector_id INTEGER NOT NULL,
              scope TEXT NOT NULL,level TEXT NOT NULL DEFAULT 'read',requires_confirmation INTEGER NOT NULL DEFAULT 1,
              enabled INTEGER NOT NULL DEFAULT 1,updated_at TEXT NOT NULL,
              UNIQUE(connector_id,scope));
            CREATE TABLE IF NOT EXISTS approval_rules(
              id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,pattern TEXT NOT NULL,
              minimum_level TEXT NOT NULL DEFAULT 'write',requires_confirmation INTEGER NOT NULL DEFAULT 1,
              notes TEXT DEFAULT '',status TEXT DEFAULT 'active',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS audit_log(
              id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,
              actor TEXT DEFAULT 'jarvis',connector TEXT DEFAULT '',action TEXT NOT NULL,
              risk TEXT DEFAULT 'read',approved INTEGER,success INTEGER,detail_json TEXT DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS modes(
              key TEXT PRIMARY KEY,value TEXT NOT NULL,updated_at TEXT NOT NULL);
            """)
            defaults={'safe_mode':'on','default_external_level':'read','draft_before_publish':'on','audit_enabled':'on'}
            now=self._now()
            for k,v in defaults.items():
                conn.execute('INSERT OR IGNORE INTO modes(key,value,updated_at) VALUES(?,?,?)',(k,v,now))

    def _now(self):return datetime.now().isoformat(timespec='seconds')
    def _rows(self,rows):return [dict(x) for x in rows]
    def _get(self,table,item_id):
        with self._connect() as c:r=c.execute(f'SELECT * FROM {table} WHERE id=?',(int(item_id),)).fetchone()
        return {'ok':bool(r),'data':dict(r) if r else None,'error':None if r else 'Registro não encontrado.'}

    def audit(self,action,connector='',risk='read',approved=None,success=None,detail=None,actor='jarvis'):
        with self._connect() as c:cur=c.execute('INSERT INTO audit_log(created_at,actor,connector,action,risk,approved,success,detail_json) VALUES(?,?,?,?,?,?,?,?)',(
            self._now(),actor,connector,action,risk,None if approved is None else int(bool(approved)),None if success is None else int(bool(success)),json.dumps(detail or {},ensure_ascii=False)))
        return {'ok':True,'id':cur.lastrowid}

    def execute(self,operation,**p):
        now=self._now()
        try:
            if operation=='connector_create':
                with self._connect() as c:cur=c.execute('INSERT INTO connectors(name,connector_type,environment,endpoint,status,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',(p['name'],p['connector_type'],p.get('environment','production'),p.get('endpoint',''),p.get('status','disabled'),p.get('notes',''),now,now))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='connector_list':
                sql='SELECT * FROM connectors';a=[]
                if p.get('status'):sql+=' WHERE status=?';a.append(p['status'])
                sql+=' ORDER BY name LIMIT ?';a.append(int(p.get('limit',200)))
                with self._connect() as c:rows=c.execute(sql,a).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}
            if operation=='connector_get':
                r=self._get('connectors',p['id'])
                if r.get('ok'):
                    with self._connect() as c:perms=c.execute('SELECT * FROM permissions WHERE connector_id=? ORDER BY scope',(int(p['id']),)).fetchall()
                    r['data']['permissions']=self._rows(perms)
                return r
            if operation=='connector_search':
                q=f"%{p['query']}%"
                with self._connect() as c:rows=c.execute('SELECT * FROM connectors WHERE name LIKE ? OR connector_type LIKE ? OR endpoint LIKE ? OR notes LIKE ? ORDER BY name LIMIT ?',(q,q,q,q,int(p.get('limit',100)))).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}
            if operation=='connector_update':
                f=[];a=[]
                for k in ('name','connector_type','environment','endpoint','status','notes'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                f.append('updated_at=?');a.append(now);a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE connectors SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='connector_enable':return self.execute('connector_update',id=p['id'],status='enabled')
            if operation=='connector_disable':return self.execute('connector_update',id=p['id'],status='disabled')
            if operation=='connector_remove':
                with self._connect() as c:
                    c.execute('DELETE FROM permissions WHERE connector_id=?',(int(p['id']),));cur=c.execute('DELETE FROM connectors WHERE id=?',(int(p['id']),))
                return {'ok':True,'removed':cur.rowcount}

            if operation=='permission_set':
                level=str(p.get('level','read')).lower()
                if level not in RISK_RANK:return {'ok':False,'error':'Nível inválido.'}
                with self._connect() as c:c.execute('''INSERT INTO permissions(connector_id,scope,level,requires_confirmation,enabled,updated_at) VALUES(?,?,?,?,?,?)
                    ON CONFLICT(connector_id,scope) DO UPDATE SET level=excluded.level,requires_confirmation=excluded.requires_confirmation,enabled=excluded.enabled,updated_at=excluded.updated_at''',(int(p['connector_id']),p['scope'],level,1 if p.get('requires_confirmation',True) else 0,1 if p.get('enabled',True) else 0,now))
                return {'ok':True}
            if operation=='permission_list':
                with self._connect() as c:rows=c.execute('SELECT * FROM permissions WHERE connector_id=? ORDER BY scope',(int(p['connector_id']),)).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}
            if operation=='permission_remove':
                with self._connect() as c:cur=c.execute('DELETE FROM permissions WHERE id=?',(int(p['id']),))
                return {'ok':True,'removed':cur.rowcount}
            if operation=='permission_check':
                connector_id=int(p['connector_id']);scope=p['scope'];requested=str(p.get('requested_level','read')).lower()
                with self._connect() as c:
                    con=c.execute('SELECT * FROM connectors WHERE id=?',(connector_id,)).fetchone();perm=c.execute('SELECT * FROM permissions WHERE connector_id=? AND scope=?',(connector_id,scope)).fetchone()
                if not con:return {'ok':False,'allowed':False,'reason':'Connector não encontrado.'}
                if con['status']!='enabled':return {'ok':True,'allowed':False,'reason':'Connector desabilitado.'}
                if not perm or not perm['enabled']:return {'ok':True,'allowed':False,'reason':'Escopo não autorizado.'}
                allowed=RISK_RANK.get(perm['level'],0)>=RISK_RANK.get(requested,99)
                return {'ok':True,'allowed':allowed,'connector':dict(con),'permission':dict(perm),'requires_confirmation':bool(perm['requires_confirmation']) and requested!='read'}
            if operation=='permission_matrix':
                with self._connect() as c:rows=c.execute('''SELECT c.id connector_id,c.name,c.connector_type,c.environment,c.status,p.scope,p.level,p.requires_confirmation,p.enabled
                    FROM connectors c LEFT JOIN permissions p ON p.connector_id=c.id ORDER BY c.name,p.scope''').fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}

            if operation=='rule_create':
                with self._connect() as c:cur=c.execute('INSERT INTO approval_rules(name,pattern,minimum_level,requires_confirmation,notes,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',(p['name'],p['pattern'],p.get('minimum_level','write'),1 if p.get('requires_confirmation',True) else 0,p.get('notes',''),p.get('status','active'),now,now))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='rule_list':
                sql='SELECT * FROM approval_rules';a=[]
                if p.get('status'):sql+=' WHERE status=?';a.append(p['status'])
                sql+=' ORDER BY name LIMIT ?';a.append(int(p.get('limit',200)))
                with self._connect() as c:rows=c.execute(sql,a).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}
            if operation=='rule_get':return self._get('approval_rules',p['id'])
            if operation=='rule_update':
                f=[];a=[]
                for k in ('name','pattern','minimum_level','notes','status'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                if 'requires_confirmation' in p:f.append('requires_confirmation=?');a.append(1 if p['requires_confirmation'] else 0)
                f.append('updated_at=?');a.append(now);a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE approval_rules SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='rule_remove':
                with self._connect() as c:cur=c.execute('DELETE FROM approval_rules WHERE id=?',(int(p['id']),))
                return {'ok':True,'removed':cur.rowcount}
            if operation=='rule_match':
                import re
                action=str(p['action']);matches=[]
                with self._connect() as c:rows=c.execute("SELECT * FROM approval_rules WHERE status='active'").fetchall()
                for r in rows:
                    try:
                        if re.search(r['pattern'],action,re.I):matches.append(dict(r))
                    except re.error:pass
                return {'ok':True,'action':action,'items':matches,'count':len(matches)}

            if operation=='mode_get':
                with self._connect() as c:rows=c.execute('SELECT * FROM modes ORDER BY key').fetchall()
                return {'ok':True,'data':{r['key']:r['value'] for r in rows}}
            if operation=='mode_set':
                with self._connect() as c:c.execute('INSERT INTO modes(key,value,updated_at) VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',(p['key'],str(p['value']),now))
                return {'ok':True,'key':p['key'],'value':str(p['value'])}
            if operation=='safe_mode_on':return self.execute('mode_set',key='safe_mode',value='on')
            if operation=='safe_mode_off':return self.execute('mode_set',key='safe_mode',value='off')

            if operation=='audit_add':return self.audit(p['action'],p.get('connector',''),p.get('risk','read'),p.get('approved'),p.get('success'),p.get('detail'),p.get('actor','jarvis'))
            if operation=='audit_list':
                with self._connect() as c:rows=c.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT ?',(int(p.get('limit',200)),)).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}
            if operation=='audit_search':
                q=f"%{p['query']}%"
                with self._connect() as c:rows=c.execute('SELECT * FROM audit_log WHERE action LIKE ? OR connector LIKE ? OR actor LIKE ? OR detail_json LIKE ? ORDER BY id DESC LIMIT ?',(q,q,q,q,int(p.get('limit',100)))).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}
            if operation=='audit_export':
                rows=self.execute('audit_list',limit=p.get('limit',10000)).get('items',[]);out=Path(p['path']).expanduser().resolve();out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rows,indent=2,ensure_ascii=False),encoding='utf-8')
                return {'ok':True,'path':str(out),'events':len(rows)}

            if operation=='stats':
                with self._connect() as c:
                    con=c.execute('SELECT COUNT(*) n FROM connectors').fetchone()['n'];per=c.execute('SELECT COUNT(*) n FROM permissions').fetchone()['n'];rules=c.execute('SELECT COUNT(*) n FROM approval_rules').fetchone()['n'];aud=c.execute('SELECT COUNT(*) n FROM audit_log').fetchone()['n']
                return {'ok':True,'connectors':con,'permissions':per,'approval_rules':rules,'audit_events':aud,'modes':self.execute('mode_get').get('data',{})}

            return {'ok':False,'error':f'Operação de governança desconhecida: {operation}'}
        except sqlite3.IntegrityError as exc:return {'ok':False,'error':f'Conflito de dados: {exc}'}
        except Exception as exc:return {'ok':False,'error':str(exc)}
