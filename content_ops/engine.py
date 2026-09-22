import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path


class ContentOps:
    def __init__(self, db_path, workspace, institutional_store=None):
        self.db_path=Path(db_path); self.db_path.parent.mkdir(parents=True,exist_ok=True)
        self.workspace=Path(workspace); self.institutional=institutional_store; self._init_db()

    def _connect(self):
        conn=sqlite3.connect(self.db_path); conn.row_factory=sqlite3.Row; return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS templates(
              id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,
              content_type TEXT NOT NULL,body TEXT NOT NULL,description TEXT DEFAULT '',
              channel TEXT DEFAULT 'general',status TEXT DEFAULT 'active',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS briefs(
              id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,topic TEXT NOT NULL,
              content_type TEXT DEFAULT 'article',channel TEXT DEFAULT 'general',objective TEXT DEFAULT '',
              audience TEXT DEFAULT '',cta TEXT DEFAULT '',sources_json TEXT DEFAULT '[]',notes TEXT DEFAULT '',
              status TEXT DEFAULT 'draft',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS drafts(
              id INTEGER PRIMARY KEY AUTOINCREMENT,brief_id INTEGER,title TEXT NOT NULL,body TEXT NOT NULL,
              content_type TEXT DEFAULT '',version INTEGER NOT NULL DEFAULT 1,status TEXT DEFAULT 'draft',
              metadata_json TEXT DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS reviews(
              id INTEGER PRIMARY KEY AUTOINCREMENT,draft_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'pending',
              reviewer TEXT DEFAULT '',notes TEXT DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS packages(
              id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,path TEXT NOT NULL,
              brief_id INTEGER,draft_id INTEGER,status TEXT DEFAULT 'prepared',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS calendars(
              id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,channel TEXT DEFAULT '',scheduled_for TEXT NOT NULL,
              brief_id INTEGER,draft_id INTEGER,status TEXT DEFAULT 'planned',notes TEXT DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            """)

    def _now(self):return datetime.now().isoformat(timespec='seconds')
    def _rows(self,rows):
        out=[]
        for r in rows:
            d=dict(r)
            for src,dst in [('sources_json','sources'),('metadata_json','metadata')]:
                if src in d:
                    raw=d.pop(src)
                    try:d[dst]=json.loads(raw or ('[]' if dst=='sources' else '{}'))
                    except Exception:d[dst]=[] if dst=='sources' else {}
            out.append(d)
        return out
    def _get(self,table,item_id):
        with self._connect() as c:r=c.execute(f'SELECT * FROM {table} WHERE id=?',(int(item_id),)).fetchone()
        return {'ok':bool(r),'data':self._rows([r])[0] if r else None,'error':None if r else 'Registro não encontrado.'}
    def _list(self,table,status=None,limit=200,order='updated_at DESC'):
        sql=f'SELECT * FROM {table}';a=[]
        if status:sql+=' WHERE status=?';a.append(status)
        sql+=f' ORDER BY {order} LIMIT ?';a.append(int(limit))
        with self._connect() as c:rows=c.execute(sql,a).fetchall()
        return {'ok':True,'items':self._rows(rows),'count':len(rows)}

    def _validate_sources(self,sources):
        items=sources if isinstance(sources,list) else []
        return {'count':len(items),'with_url':sum(1 for x in items if isinstance(x,dict) and x.get('url')),
                'official':sum(1 for x in items if isinstance(x,dict) and x.get('official'))}

    def _check_body(self,body,content_type='article'):
        body=str(body); words=re.findall(r'\b[\wÀ-ÿ-]+\b',body); links=re.findall(r'https?://\S+',body)
        headings=len(re.findall(r'(?m)^#{1,6}\s+',body)); bullets=len(re.findall(r'(?m)^\s*[-*•]\s+',body))
        cta=bool(re.search(r'(?i)entre em contato|saiba mais|confira|acesse|associe|fale com|consulte',body))
        return {'chars':len(body),'words':len(words),'links':len(links),'headings':headings,'bullets':bullets,'has_cta':cta,
                'content_type':content_type}

    def execute(self,operation,**p):
        now=self._now()
        try:
            if operation=='template_create':
                with self._connect() as c:cur=c.execute('INSERT INTO templates(name,content_type,body,description,channel,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',(p['name'],p['content_type'],p['body'],p.get('description',''),p.get('channel','general'),p.get('status','active'),now,now))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='template_list':return self._list('templates',p.get('status'),p.get('limit',200),'name')
            if operation=='template_get':return self._get('templates',p['id'])
            if operation=='template_search':
                q=f"%{p['query']}%"
                with self._connect() as c:rows=c.execute('SELECT * FROM templates WHERE name LIKE ? OR description LIKE ? OR content_type LIKE ? OR channel LIKE ? ORDER BY name LIMIT ?',(q,q,q,q,int(p.get('limit',100)))).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}
            if operation=='template_update':
                f=[];a=[]
                for k in ('name','content_type','body','description','channel','status'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                f.append('updated_at=?');a.append(now);a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE templates SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='template_archive':return self.execute('template_update',id=p['id'],status='archived')
            if operation=='template_render':
                t=self._get('templates',p['id']);
                if not t.get('ok'):return t
                body=t['data']['body'];values=p.get('values',{}) or {}
                for k,v in values.items():body=body.replace('{{'+str(k)+'}}',str(v))
                missing=re.findall(r'\{\{([^}]+)\}\}',body)
                return {'ok':True,'text':body,'missing':missing,'template':t['data']}

            if operation=='brief_create':
                with self._connect() as c:cur=c.execute('INSERT INTO briefs(title,topic,content_type,channel,objective,audience,cta,sources_json,notes,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(p['title'],p['topic'],p.get('content_type','article'),p.get('channel','general'),p.get('objective',''),p.get('audience',''),p.get('cta',''),json.dumps(p.get('sources',[]),ensure_ascii=False),p.get('notes',''),p.get('status','draft'),now,now))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='brief_list':return self._list('briefs',p.get('status'),p.get('limit',200))
            if operation=='brief_get':return self._get('briefs',p['id'])
            if operation=='brief_search':
                q=f"%{p['query']}%"
                with self._connect() as c:rows=c.execute('SELECT * FROM briefs WHERE title LIKE ? OR topic LIKE ? OR objective LIKE ? OR audience LIKE ? ORDER BY updated_at DESC LIMIT ?',(q,q,q,q,int(p.get('limit',100)))).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}
            if operation=='brief_update':
                f=[];a=[]
                for k in ('title','topic','content_type','channel','objective','audience','cta','notes','status'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                if 'sources' in p:f.append('sources_json=?');a.append(json.dumps(p['sources'],ensure_ascii=False))
                f.append('updated_at=?');a.append(now);a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE briefs SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='brief_set_status':return self.execute('brief_update',id=p['id'],status=p['status'])
            if operation=='brief_source_report':
                b=self._get('briefs',p['id']);
                if not b.get('ok'):return b
                return {'ok':True,'brief_id':int(p['id']),**self._validate_sources(b['data'].get('sources',[]))}

            if operation=='draft_create':
                version=int(p.get('version',1))
                if p.get('brief_id') and 'version' not in p:
                    with self._connect() as c:version=c.execute('SELECT COALESCE(MAX(version),0)+1 n FROM drafts WHERE brief_id=?',(int(p['brief_id']),)).fetchone()['n']
                with self._connect() as c:cur=c.execute('INSERT INTO drafts(brief_id,title,body,content_type,version,status,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(p.get('brief_id'),p['title'],p['body'],p.get('content_type',''),version,p.get('status','draft'),json.dumps(p.get('metadata',{}),ensure_ascii=False),now,now))
                return {'ok':True,'id':cur.lastrowid,'version':version}
            if operation=='draft_list':return self._list('drafts',p.get('status'),p.get('limit',200))
            if operation=='draft_get':return self._get('drafts',p['id'])
            if operation=='draft_versions':
                with self._connect() as c:rows=c.execute('SELECT * FROM drafts WHERE brief_id=? ORDER BY version DESC',(int(p['brief_id']),)).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}
            if operation=='draft_update':
                f=[];a=[]
                for k in ('title','body','content_type','version','status'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                if 'metadata' in p:f.append('metadata_json=?');a.append(json.dumps(p['metadata'],ensure_ascii=False))
                f.append('updated_at=?');a.append(now);a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE drafts SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='draft_check':
                d=self._get('drafts',p['id']);
                if not d.get('ok'):return d
                return {'ok':True,'draft_id':int(p['id']),'metrics':self._check_body(d['data']['body'],d['data'].get('content_type','article'))}
            if operation=='draft_compare':
                import difflib
                a=self._get('drafts',p['draft_a']);b=self._get('drafts',p['draft_b'])
                if not a.get('ok'):return a
                if not b.get('ok'):return b
                ta=a['data']['body'];tb=b['data']['body'];ratio=difflib.SequenceMatcher(None,ta,tb).ratio()
                diff='\n'.join(difflib.unified_diff(ta.splitlines(),tb.splitlines(),fromfile=f"draft-{p['draft_a']}",tofile=f"draft-{p['draft_b']}",lineterm=''))
                return {'ok':True,'similarity':round(ratio,4),'diff':diff[:30000]}

            if operation=='review_submit':
                with self._connect() as c:
                    cur=c.execute('INSERT INTO reviews(draft_id,status,reviewer,notes,created_at,updated_at) VALUES(?,?,?,?,?,?)',(int(p['draft_id']),'pending',p.get('reviewer',''),p.get('notes',''),now,now));c.execute("UPDATE drafts SET status='review',updated_at=? WHERE id=?",(now,int(p['draft_id'])))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='review_list':return self._list('reviews',p.get('status'),p.get('limit',200))
            if operation=='review_get':return self._get('reviews',p['id'])
            if operation in {'review_approve','review_changes','review_reject'}:
                status={'review_approve':'approved','review_changes':'changes_requested','review_reject':'rejected'}[operation]
                with self._connect() as c:
                    row=c.execute('SELECT draft_id FROM reviews WHERE id=?',(int(p['id']),)).fetchone()
                    cur=c.execute('UPDATE reviews SET status=?,reviewer=?,notes=?,updated_at=? WHERE id=?',(status,p.get('reviewer',''),p.get('notes',''),now,int(p['id'])))
                    if row:c.execute('UPDATE drafts SET status=?,updated_at=? WHERE id=?',(status,now,row['draft_id']))
                return {'ok':True,'updated':cur.rowcount,'status':status}

            if operation=='package_create':
                name=re.sub(r'[^\w.-]+','_',str(p['name']).strip()) or 'package'
                folder=(self.workspace/'ContentPackages'/f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name}").resolve();folder.mkdir(parents=True,exist_ok=True)
                brief=self._get('briefs',p['brief_id'])['data'] if p.get('brief_id') else None
                draft=self._get('drafts',p['draft_id'])['data'] if p.get('draft_id') else None
                if brief:(folder/'brief.json').write_text(json.dumps(brief,indent=2,ensure_ascii=False),encoding='utf-8')
                if draft:(folder/'draft.md').write_text(f"# {draft['title']}\n\n{draft['body']}",encoding='utf-8')
                checklist=['Fontes verificadas','Texto revisado','CTA conferida','Imagem/asset conferido','Aprovação registrada']
                (folder/'checklist.md').write_text('# Checklist\n\n'+'\n'.join(f'- [ ] {x}' for x in checklist),encoding='utf-8')
                sources=(brief or {}).get('sources',[]) if brief else []
                (folder/'sources.json').write_text(json.dumps(sources,indent=2,ensure_ascii=False),encoding='utf-8')
                with self._connect() as c:cur=c.execute('INSERT INTO packages(name,path,brief_id,draft_id,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(name,str(folder),p.get('brief_id'),p.get('draft_id'),'prepared',now,now))
                return {'ok':True,'id':cur.lastrowid,'path':str(folder)}
            if operation=='package_list':return self._list('packages',p.get('status'),p.get('limit',200))
            if operation=='package_get':return self._get('packages',p['id'])
            if operation=='package_set_status':
                with self._connect() as c:cur=c.execute('UPDATE packages SET status=?,updated_at=? WHERE id=?',(p['status'],now,int(p['id'])))
                return {'ok':True,'updated':cur.rowcount}

            if operation=='calendar_add':
                with self._connect() as c:cur=c.execute('INSERT INTO calendars(title,channel,scheduled_for,brief_id,draft_id,status,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(p['title'],p.get('channel',''),p['scheduled_for'],p.get('brief_id'),p.get('draft_id'),p.get('status','planned'),p.get('notes',''),now,now))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='calendar_list':return self._list('calendars',p.get('status'),p.get('limit',300),'scheduled_for')
            if operation=='calendar_range':
                with self._connect() as c:rows=c.execute('SELECT * FROM calendars WHERE scheduled_for>=? AND scheduled_for<=? ORDER BY scheduled_for',(p['start'],p['end'])).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}
            if operation=='calendar_update':
                f=[];a=[]
                for k in ('title','channel','scheduled_for','brief_id','draft_id','status','notes'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                f.append('updated_at=?');a.append(now);a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE calendars SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='calendar_remove':
                with self._connect() as c:cur=c.execute('DELETE FROM calendars WHERE id=?',(int(p['id']),))
                return {'ok':True,'removed':cur.rowcount}

            if operation=='editorial_context':
                styles=[]
                if self.institutional:
                    styles=self.institutional.execute('style_list',status='active',limit=p.get('style_limit',50)).get('items',[])
                return {'ok':True,'style_rules':styles,'channel':p.get('channel','general'),'content_type':p.get('content_type','')}
            if operation=='stats':
                with self._connect() as c:
                    tables=['templates','briefs','drafts','reviews','packages','calendars']
                    d={t:c.execute(f'SELECT COUNT(*) n FROM {t}').fetchone()['n'] for t in tables}
                return {'ok':True,**d}

            return {'ok':False,'error':f'Operação de conteúdo institucional desconhecida: {operation}'}
        except sqlite3.IntegrityError as exc:return {'ok':False,'error':f'Conflito de dados: {exc}'}
        except Exception as exc:return {'ok':False,'error':str(exc)}
