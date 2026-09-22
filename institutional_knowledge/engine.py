import json
import re
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


class InstitutionalKnowledge:
    def __init__(self, db_path, knowledge_base, document_engine, workspace):
        self.db_path=Path(db_path); self.db_path.parent.mkdir(parents=True,exist_ok=True)
        self.kb=knowledge_base; self.docs=document_engine; self.workspace=Path(workspace)
        self._init_db()

    def _connect(self):
        conn=sqlite3.connect(self.db_path); conn.row_factory=sqlite3.Row; return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS cct_documents(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              title TEXT NOT NULL, path TEXT NOT NULL UNIQUE,
              category TEXT DEFAULT '', territory TEXT DEFAULT '',
              base_date TEXT DEFAULT '', valid_from TEXT DEFAULT '', valid_to TEXT DEFAULT '',
              collection TEXT DEFAULT 'cct', sha256 TEXT DEFAULT '',
              created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS cct_clauses(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              cct_id INTEGER NOT NULL, clause_number TEXT DEFAULT '',
              title TEXT DEFAULT '', body TEXT NOT NULL, order_index INTEGER NOT NULL,
              FOREIGN KEY(cct_id) REFERENCES cct_documents(id)
            );
            CREATE INDEX IF NOT EXISTS idx_cct_clause_doc ON cct_clauses(cct_id,order_index);
            CREATE INDEX IF NOT EXISTS idx_cct_clause_title ON cct_clauses(title);
            CREATE TABLE IF NOT EXISTS faq(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              question TEXT NOT NULL, answer TEXT NOT NULL,
              role TEXT DEFAULT '', category TEXT DEFAULT '', source TEXT DEFAULT '',
              status TEXT NOT NULL DEFAULT 'draft', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            """)

    def _now(self): return datetime.now().isoformat(timespec='seconds')

    def _extract_clauses(self,text):
        text=str(text).replace('\r\n','\n')
        patterns=[
          r'(?im)^\s*(CL[ÁA]USULA\s+(?:\d+|[A-ZÇÃÕÁÉÍÓÚ -]+?)(?:\s*[-–—:]\s*|\n))',
          r'(?im)^\s*((?:CL[ÁA]USULA|Cláusula)\s+\S+[^\n]{0,120})$'
        ]
        matches=[]
        for patt in patterns:
            matches=list(re.finditer(patt,text))
            if len(matches)>=2: break
        clauses=[]
        if not matches:
            # fallback by numbered all-caps headings
            matches=list(re.finditer(r'(?m)^\s*((?:\d+\.?)+\s+[A-ZÁÉÍÓÚÃÕÇ][^\n]{3,120})$',text))
        if not matches:
            return [{"number":"","title":"DOCUMENTO COMPLETO","body":text.strip()}]
        for i,m in enumerate(matches):
            start=m.start(); end=matches[i+1].start() if i+1<len(matches) else len(text)
            block=text[start:end].strip()
            header=re.sub(r'\s+',' ',m.group(1)).strip(' -–—:\n\t')
            num=''
            n=re.search(r'(?i)cl[áa]usula\s+([^\s:–—-]+)',header)
            if n:num=n.group(1)
            body=block[len(m.group(0)):].strip() if block.startswith(m.group(0).strip()) else block
            clauses.append({"number":num,"title":header[:240],"body":body or block})
        return clauses

    def import_file(self,path,title=None,collection='cct',category='',territory='',base_date='',valid_from='',valid_to=''):
        r=self.docs.extract_text(path,max_chars=2_000_000)
        if not r.get('ok'): return r
        h=self.docs.execute('sha256',path=path)
        text=r.get('text',''); p=Path(path).expanduser().resolve(); now=self._now()
        kb=self.kb.ingest_file(collection,p,title=title or p.name)
        if not kb.get('ok'): return kb
        clauses=self._extract_clauses(text)
        with self._connect() as conn:
            old=conn.execute('SELECT id FROM cct_documents WHERE path=?',(str(p),)).fetchone()
            if old:
                cct_id=int(old['id']); conn.execute('DELETE FROM cct_clauses WHERE cct_id=?',(cct_id,))
                conn.execute('''UPDATE cct_documents SET title=?,category=?,territory=?,base_date=?,valid_from=?,valid_to=?,collection=?,sha256=?,updated_at=? WHERE id=?''',
                    (title or p.name,category,territory,base_date,valid_from,valid_to,collection,h.get('sha256',''),now,cct_id))
            else:
                cur=conn.execute('''INSERT INTO cct_documents(title,path,category,territory,base_date,valid_from,valid_to,collection,sha256,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)''',
                    (title or p.name,str(p),category,territory,base_date,valid_from,valid_to,collection,h.get('sha256',''),now,now)); cct_id=int(cur.lastrowid)
            for idx,c in enumerate(clauses,1):
                conn.execute('INSERT INTO cct_clauses(cct_id,clause_number,title,body,order_index) VALUES(?,?,?,?,?)',(cct_id,c['number'],c['title'],c['body'],idx))
        return {'ok':True,'cct_id':cct_id,'clauses':len(clauses),'knowledge_document_id':kb.get('document_id'),'collection':collection}

    def import_folder(self,folder,collection='institutional',recursive=True,limit=500):
        inv=self.docs.inventory(folder,recursive,limit)
        if not inv.get('ok'):return inv
        items=[]
        for f in inv.get('items',[]):
            if not f.get('supported'):continue
            r=self.kb.ingest_file(collection,f['path'])
            items.append({'path':f['path'],'ok':r.get('ok'),'duplicate':r.get('duplicate',False),'error':r.get('error')})
        return {'ok':True,'collection':collection,'items':items,'count':len(items),'success':sum(1 for x in items if x['ok'])}

    def list_ccts(self,limit=200):
        with self._connect() as conn: rows=conn.execute('SELECT * FROM cct_documents ORDER BY updated_at DESC LIMIT ?',(int(limit),)).fetchall()
        return {'ok':True,'items':[dict(x) for x in rows],'count':len(rows)}

    def cct_info(self,cct_id):
        with self._connect() as conn:
            d=conn.execute('SELECT * FROM cct_documents WHERE id=?',(int(cct_id),)).fetchone()
            n=conn.execute('SELECT COUNT(*) n FROM cct_clauses WHERE cct_id=?',(int(cct_id),)).fetchone()['n'] if d else 0
        return {'ok':bool(d),'data':({**dict(d),'clauses':n} if d else None),'error':None if d else 'CCT não encontrada.'}

    def list_clauses(self,cct_id,limit=500):
        with self._connect() as conn: rows=conn.execute('SELECT id,clause_number,title,order_index FROM cct_clauses WHERE cct_id=? ORDER BY order_index LIMIT ?',(int(cct_id),int(limit))).fetchall()
        return {'ok':True,'items':[dict(x) for x in rows],'count':len(rows)}

    def get_clause(self,clause_id):
        with self._connect() as conn: row=conn.execute('SELECT c.*,d.title cct_title,d.path FROM cct_clauses c JOIN cct_documents d ON d.id=c.cct_id WHERE c.id=?',(int(clause_id),)).fetchone()
        return {'ok':bool(row),'data':dict(row) if row else None,'error':None if row else 'Cláusula não encontrada.'}

    def search_clauses(self,query,cct_id=None,limit=40):
        q=f"%{str(query).strip()}%"; args=[]
        sql='''SELECT c.id,c.cct_id,c.clause_number,c.title,c.order_index,d.title cct_title,d.path,
               substr(c.body,1,1600) body FROM cct_clauses c JOIN cct_documents d ON d.id=c.cct_id WHERE (c.title LIKE ? OR c.body LIKE ?)'''
        args=[q,q]
        if cct_id is not None: sql+=' AND c.cct_id=?';args.append(int(cct_id))
        sql+=' ORDER BY c.cct_id,c.order_index LIMIT ?';args.append(int(limit))
        with self._connect() as conn: rows=conn.execute(sql,args).fetchall()
        items=[]
        for r in rows:
            d=dict(r); d['citation']=f"[CCT:{d['cct_id']}/clause:{d['id']}]";items.append(d)
        return {'ok':True,'items':items,'count':len(items),'query':query}

    def compare_ccts(self,cct_a,cct_b):
        with self._connect() as conn:
            a=conn.execute('SELECT id,clause_number,title,body,order_index FROM cct_clauses WHERE cct_id=? ORDER BY order_index',(int(cct_a),)).fetchall()
            b=conn.execute('SELECT id,clause_number,title,body,order_index FROM cct_clauses WHERE cct_id=? ORDER BY order_index',(int(cct_b),)).fetchall()
        def key(r):
            title=re.sub(r'\W+',' ',(r['title'] or '').lower()).strip()
            num=(r['clause_number'] or '').lower(); return num or title[:80]
        amap={key(x):x for x in a};bmap={key(x):x for x in b}; allkeys=list(dict.fromkeys(list(amap)+list(bmap)))
        added=[];removed=[];changed=[];same=[]
        import difflib
        for k in allkeys:
            x=amap.get(k);y=bmap.get(k)
            if x is None: added.append({'key':k,'title':y['title'],'new_clause_id':y['id']});continue
            if y is None: removed.append({'key':k,'title':x['title'],'old_clause_id':x['id']});continue
            ratio=difflib.SequenceMatcher(None,x['body'],y['body']).ratio()
            item={'key':k,'title_old':x['title'],'title_new':y['title'],'old_clause_id':x['id'],'new_clause_id':y['id'],'similarity':round(ratio,4)}
            (same if ratio>=0.985 else changed).append(item)
        return {'ok':True,'cct_a':int(cct_a),'cct_b':int(cct_b),'added':added,'removed':removed,'changed':changed,'same':same,
                'summary':{'added':len(added),'removed':len(removed),'changed':len(changed),'same':len(same)}}

    def evidence_pack(self,query,collections=None,limit=10,max_chars=7000):
        cols=collections or [x['collection'] for x in self.kb.list_collections().get('items',[])]
        gathered=[]
        seen=set()
        for col in cols:
            r=self.kb.search(col,query,limit=max(3,int(limit)))
            for item in r.get('items',[]):
                key=(item.get('document_id'),item.get('chunk_id'))
                if key in seen:continue
                seen.add(key)
                gathered.append({**item,'collection':col,'citation':f"[KB:{col}/doc:{item.get('document_id')}/chunk:{item.get('chunk_id')}]"})
        # Put exact phrase matches first, then FTS score where lower is usually better.
        q=str(query).lower()
        gathered.sort(key=lambda x:(0 if q in (x.get('text','').lower()) else 1, x.get('score',999999)))
        out=[]; chars=0
        for x in gathered[:int(limit)*2]:
            excerpt=re.sub(r'\s+',' ',x.get('text','')).strip()[:1600]
            if chars+len(excerpt)>int(max_chars):break
            y=dict(x);y['text']=excerpt;out.append(y);chars+=len(excerpt)
            if len(out)>=int(limit):break
        return {'ok':True,'query':query,'items':out,'count':len(out),'chars':chars,'collections':cols}

    def search_all(self,query,limit_per_collection=5):
        cols=[x['collection'] for x in self.kb.list_collections().get('items',[])]
        items=[]
        for col in cols:
            r=self.kb.search(col,query,limit=int(limit_per_collection))
            for x in r.get('items',[]):items.append({**x,'collection':col,'citation':f"[KB:{col}/doc:{x.get('document_id')}/chunk:{x.get('chunk_id')}]"})
        return {'ok':True,'items':items,'count':len(items),'collections':cols}

    def provenance(self,document_id):
        r=self.kb.document_info(document_id)
        if not r.get('ok'):return r
        d=r['data'];return {'ok':True,'document':d,'citation_base':f"[KB:{d.get('collection')}/doc:{d.get('id')}]"}

    def collection_health(self,collection):
        docs=self.kb.list_documents(collection,limit=10000).get('items',[])
        dates=[]
        for d in docs:
            try:dates.append(datetime.fromisoformat(d.get('created_at')))
            except Exception:pass
        newest=max(dates).isoformat(timespec='seconds') if dates else None
        oldest=min(dates).isoformat(timespec='seconds') if dates else None
        return {'ok':True,'collection':collection,'documents':len(docs),'newest':newest,'oldest':oldest}

    def stale_documents(self,collection,days=365):
        docs=self.kb.list_documents(collection,limit=10000).get('items',[]);cut=datetime.now()-timedelta(days=int(days));items=[]
        for d in docs:
            try:
                if datetime.fromisoformat(d.get('created_at'))<cut:items.append(d)
            except Exception:pass
        return {'ok':True,'collection':collection,'days':int(days),'items':items,'count':len(items)}

    def duplicates(self,collection):
        docs=self.kb.list_documents(collection,limit=10000).get('items',[]);by={};dups=[]
        for d in docs:
            src=d.get('source',''); by.setdefault(src,[]).append(d)
        for src,items in by.items():
            if src and len(items)>1:dups.append({'source':src,'documents':items,'count':len(items)})
        return {'ok':True,'items':dups,'count':len(dups)}

    def faq_create(self,question,answer,role='',category='',source='',status='draft'):
        now=self._now()
        with self._connect() as conn:cur=conn.execute('INSERT INTO faq(question,answer,role,category,source,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)',(question,answer,role,category,source,status,now,now))
        return {'ok':True,'id':cur.lastrowid}
    def faq_list(self,status=None,limit=200):
        sql='SELECT * FROM faq';args=[]
        if status:sql+=' WHERE status=?';args.append(status)
        sql+=' ORDER BY updated_at DESC LIMIT ?';args.append(int(limit))
        with self._connect() as conn:rows=conn.execute(sql,args).fetchall()
        return {'ok':True,'items':[dict(x) for x in rows],'count':len(rows)}
    def faq_search(self,query,role=None,limit=50):
        q=f"%{query}%";sql='SELECT * FROM faq WHERE (question LIKE ? OR answer LIKE ? OR category LIKE ?)';args=[q,q,q]
        if role:sql+=' AND (role=? OR role="")';args.append(role)
        sql+=' ORDER BY updated_at DESC LIMIT ?';args.append(int(limit))
        with self._connect() as conn:rows=conn.execute(sql,args).fetchall()
        return {'ok':True,'items':[dict(x) for x in rows],'count':len(rows)}
    def faq_update(self,item_id,**p):
        fields=[];args=[]
        for k in ('question','answer','role','category','source','status'):
            if k in p and p[k] is not None:fields.append(f'{k}=?');args.append(p[k])
        fields.append('updated_at=?');args.append(self._now());args.append(int(item_id))
        with self._connect() as conn:cur=conn.execute(f"UPDATE faq SET {', '.join(fields)} WHERE id=?",args)
        return {'ok':True,'updated':cur.rowcount}
    def faq_remove(self,item_id):
        with self._connect() as conn:cur=conn.execute('DELETE FROM faq WHERE id=?',(int(item_id),))
        return {'ok':True,'removed':cur.rowcount}

    def stats(self):
        with self._connect() as conn:
            cct=conn.execute('SELECT COUNT(*) n FROM cct_documents').fetchone()['n'];clauses=conn.execute('SELECT COUNT(*) n FROM cct_clauses').fetchone()['n'];faq=conn.execute('SELECT COUNT(*) n FROM faq').fetchone()['n']
        kb=self.kb.stats()
        return {'ok':True,'ccts':cct,'clauses':clauses,'faq':faq,'knowledge':kb}

    def execute(self,operation,**p):
        if operation=='import_file':return self.import_file(**p)
        if operation=='import_folder':return self.import_folder(**p)
        if operation=='cct_list':return self.list_ccts(p.get('limit',200))
        if operation=='cct_info':return self.cct_info(p['cct_id'])
        if operation=='clause_list':return self.list_clauses(p['cct_id'],p.get('limit',500))
        if operation=='clause_get':return self.get_clause(p['clause_id'])
        if operation=='clause_search':return self.search_clauses(p['query'],p.get('cct_id'),p.get('limit',40))
        if operation=='cct_compare':return self.compare_ccts(p['cct_a'],p['cct_b'])
        if operation=='evidence_pack':return self.evidence_pack(p['query'],p.get('collections'),p.get('limit',10),p.get('max_chars',7000))
        if operation=='search_all':return self.search_all(p['query'],p.get('limit_per_collection',5))
        if operation=='provenance':return self.provenance(p['document_id'])
        if operation=='collection_health':return self.collection_health(p['collection'])
        if operation=='stale_documents':return self.stale_documents(p['collection'],p.get('days',365))
        if operation=='duplicates':return self.duplicates(p['collection'])
        if operation=='faq_create':return self.faq_create(**p)
        if operation=='faq_list':return self.faq_list(p.get('status'),p.get('limit',200))
        if operation=='faq_search':return self.faq_search(p['query'],p.get('role'),p.get('limit',50))
        if operation=='faq_update':
            item_id=p.pop('id');return self.faq_update(item_id,**p)
        if operation=='faq_remove':return self.faq_remove(p['id'])
        if operation=='stats':return self.stats()
        return {'ok':False,'error':f'Operação de conhecimento institucional desconhecida: {operation}'}
