import json
import sqlite3
from datetime import datetime
from pathlib import Path


class TrainingEngine:
    def __init__(self, db_path, knowledge_engine=None):
        self.db_path=Path(db_path); self.db_path.parent.mkdir(parents=True,exist_ok=True)
        self.knowledge=knowledge_engine; self._init_db()

    def _connect(self):
        conn=sqlite3.connect(self.db_path); conn.row_factory=sqlite3.Row; return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS tracks(
              id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,
              role TEXT DEFAULT '',description TEXT DEFAULT '',status TEXT DEFAULT 'active',
              created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS modules(
              id INTEGER PRIMARY KEY AUTOINCREMENT,track_id INTEGER NOT NULL,
              title TEXT NOT NULL,description TEXT DEFAULT '',order_index INTEGER NOT NULL DEFAULT 1,
              collection TEXT DEFAULT '',query TEXT DEFAULT '',status TEXT DEFAULT 'active',
              created_at TEXT NOT NULL,updated_at TEXT NOT NULL,
              FOREIGN KEY(track_id) REFERENCES tracks(id));
            CREATE TABLE IF NOT EXISTS quizzes(
              id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,role TEXT DEFAULT '',
              module_id INTEGER,description TEXT DEFAULT '',status TEXT DEFAULT 'active',
              created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS questions(
              id INTEGER PRIMARY KEY AUTOINCREMENT,quiz_id INTEGER NOT NULL,
              question TEXT NOT NULL,answer TEXT NOT NULL,explanation TEXT DEFAULT '',
              source TEXT DEFAULT '',difficulty TEXT DEFAULT 'normal',order_index INTEGER NOT NULL DEFAULT 1,
              FOREIGN KEY(quiz_id) REFERENCES quizzes(id));
            CREATE TABLE IF NOT EXISTS checklists(
              id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL,role TEXT DEFAULT '',
              description TEXT DEFAULT '',status TEXT DEFAULT 'active',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS checklist_items(
              id INTEGER PRIMARY KEY AUTOINCREMENT,checklist_id INTEGER NOT NULL,
              text TEXT NOT NULL,order_index INTEGER NOT NULL DEFAULT 1,required INTEGER NOT NULL DEFAULT 1,
              source TEXT DEFAULT '',FOREIGN KEY(checklist_id) REFERENCES checklists(id));
            CREATE TABLE IF NOT EXISTS learners(
              id INTEGER PRIMARY KEY AUTOINCREMENT,alias TEXT NOT NULL UNIQUE,role TEXT DEFAULT '',
              notes TEXT DEFAULT '',status TEXT DEFAULT 'active',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS progress(
              id INTEGER PRIMARY KEY AUTOINCREMENT,learner_id INTEGER NOT NULL,item_type TEXT NOT NULL,
              item_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'pending',score REAL,
              completed_at TEXT,notes TEXT DEFAULT '',updated_at TEXT NOT NULL,
              UNIQUE(learner_id,item_type,item_id));
            CREATE TABLE IF NOT EXISTS scenarios(
              id INTEGER PRIMARY KEY AUTOINCREMENT,title TEXT NOT NULL,role TEXT DEFAULT '',
              prompt TEXT NOT NULL,expected_points TEXT DEFAULT '',source TEXT DEFAULT '',
              difficulty TEXT DEFAULT 'normal',status TEXT DEFAULT 'active',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            """)

    def _now(self):return datetime.now().isoformat(timespec='seconds')
    def _rows(self,rows):return [dict(x) for x in rows]
    def _list(self,table,status=None,limit=200,order='id DESC'):
        sql=f'SELECT * FROM {table}';args=[]
        if status:sql+=' WHERE status=?';args.append(status)
        sql+=f' ORDER BY {order} LIMIT ?';args.append(int(limit))
        with self._connect() as conn:rows=conn.execute(sql,args).fetchall()
        return {'ok':True,'items':self._rows(rows),'count':len(rows)}
    def _get(self,table,item_id):
        with self._connect() as conn:r=conn.execute(f'SELECT * FROM {table} WHERE id=?',(int(item_id),)).fetchone()
        return {'ok':bool(r),'data':dict(r) if r else None,'error':None if r else 'Registro não encontrado.'}

    def execute(self,operation,**p):
        now=self._now()
        try:
            if operation=='track_create':
                with self._connect() as c:cur=c.execute('INSERT INTO tracks(name,role,description,status,created_at,updated_at) VALUES(?,?,?,?,?,?)',(p['name'],p.get('role',''),p.get('description',''),p.get('status','active'),now,now))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='track_list':return self._list('tracks',p.get('status'),p.get('limit',100),'name')
            if operation=='track_get':
                r=self._get('tracks',p['id'])
                if r.get('ok'):
                    with self._connect() as c:mods=c.execute('SELECT * FROM modules WHERE track_id=? ORDER BY order_index,id',(int(p['id']),)).fetchall()
                    r['data']['modules']=self._rows(mods)
                return r
            if operation=='track_update':
                f=[];a=[]
                for k in ('name','role','description','status'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                f.append('updated_at=?');a.append(now);a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE tracks SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='track_archive':return self.execute('track_update',id=p['id'],status='archived')
            if operation=='track_search':
                q=f"%{p['query']}%"
                with self._connect() as c:rows=c.execute('SELECT * FROM tracks WHERE name LIKE ? OR role LIKE ? OR description LIKE ? ORDER BY name LIMIT ?',(q,q,q,int(p.get('limit',100)))).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}

            if operation=='module_add':
                order=p.get('order_index')
                if order is None:
                    with self._connect() as c:row=c.execute('SELECT COALESCE(MAX(order_index),0)+1 n FROM modules WHERE track_id=?',(int(p['track_id']),)).fetchone();order=row['n']
                with self._connect() as c:cur=c.execute('INSERT INTO modules(track_id,title,description,order_index,collection,query,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(int(p['track_id']),p['title'],p.get('description',''),int(order),p.get('collection',''),p.get('query',''),p.get('status','active'),now,now))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='module_list':
                with self._connect() as c:rows=c.execute('SELECT * FROM modules WHERE track_id=? ORDER BY order_index,id',(int(p['track_id']),)).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}
            if operation=='module_get':return self._get('modules',p['id'])
            if operation=='module_update':
                f=[];a=[]
                for k in ('title','description','order_index','collection','query','status'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                f.append('updated_at=?');a.append(now);a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE modules SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='module_remove':
                with self._connect() as c:cur=c.execute('DELETE FROM modules WHERE id=?',(int(p['id']),))
                return {'ok':True,'removed':cur.rowcount}
            if operation=='module_material':
                m=self._get('modules',p['id'])
                if not m.get('ok'):return m
                d=m['data'];collection=d.get('collection');query=d.get('query') or d.get('title')
                if not self.knowledge or not collection:return {'ok':True,'module':d,'evidence':[]}
                ev=self.knowledge.evidence_pack(query,[collection],p.get('limit',8),p.get('max_chars',6000))
                return {'ok':True,'module':d,'evidence':ev.get('items',[]),'citations':[x.get('citation') for x in ev.get('items',[])]}

            if operation=='quiz_create':
                with self._connect() as c:cur=c.execute('INSERT INTO quizzes(name,role,module_id,description,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?)',(p['name'],p.get('role',''),p.get('module_id'),p.get('description',''),p.get('status','active'),now,now))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='quiz_list':return self._list('quizzes',p.get('status'),p.get('limit',100),'updated_at DESC')
            if operation=='quiz_get':
                r=self._get('quizzes',p['id'])
                if r.get('ok'):
                    with self._connect() as c:q=c.execute('SELECT * FROM questions WHERE quiz_id=? ORDER BY order_index,id',(int(p['id']),)).fetchall()
                    r['data']['questions']=self._rows(q)
                return r
            if operation=='quiz_update':
                f=[];a=[]
                for k in ('name','role','module_id','description','status'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                f.append('updated_at=?');a.append(now);a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE quizzes SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='quiz_archive':return self.execute('quiz_update',id=p['id'],status='archived')
            if operation=='question_add':
                order=p.get('order_index')
                if order is None:
                    with self._connect() as c:order=c.execute('SELECT COALESCE(MAX(order_index),0)+1 n FROM questions WHERE quiz_id=?',(int(p['quiz_id']),)).fetchone()['n']
                with self._connect() as c:cur=c.execute('INSERT INTO questions(quiz_id,question,answer,explanation,source,difficulty,order_index) VALUES(?,?,?,?,?,?,?)',(int(p['quiz_id']),p['question'],p['answer'],p.get('explanation',''),p.get('source',''),p.get('difficulty','normal'),int(order)))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='question_update':
                f=[];a=[]
                for k in ('question','answer','explanation','source','difficulty','order_index'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE questions SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='question_remove':
                with self._connect() as c:cur=c.execute('DELETE FROM questions WHERE id=?',(int(p['id']),))
                return {'ok':True,'removed':cur.rowcount}
            if operation=='quiz_answer_key':
                q=self.execute('quiz_get',id=p['id']);
                if not q.get('ok'):return q
                items=[{'question':x['question'],'answer':x['answer'],'explanation':x['explanation'],'source':x['source']} for x in q['data']['questions']]
                return {'ok':True,'quiz':q['data']['name'],'items':items,'count':len(items)}

            if operation=='checklist_create':
                with self._connect() as c:cur=c.execute('INSERT INTO checklists(name,role,description,status,created_at,updated_at) VALUES(?,?,?,?,?,?)',(p['name'],p.get('role',''),p.get('description',''),p.get('status','active'),now,now))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='checklist_list':return self._list('checklists',p.get('status'),p.get('limit',100),'name')
            if operation=='checklist_get':
                r=self._get('checklists',p['id'])
                if r.get('ok'):
                    with self._connect() as c:items=c.execute('SELECT * FROM checklist_items WHERE checklist_id=? ORDER BY order_index,id',(int(p['id']),)).fetchall()
                    r['data']['items']=self._rows(items)
                return r
            if operation=='checklist_update':
                f=[];a=[]
                for k in ('name','role','description','status'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                f.append('updated_at=?');a.append(now);a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE checklists SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='checklist_archive':return self.execute('checklist_update',id=p['id'],status='archived')
            if operation=='checklist_item_add':
                order=p.get('order_index')
                if order is None:
                    with self._connect() as c:order=c.execute('SELECT COALESCE(MAX(order_index),0)+1 n FROM checklist_items WHERE checklist_id=?',(int(p['checklist_id']),)).fetchone()['n']
                with self._connect() as c:cur=c.execute('INSERT INTO checklist_items(checklist_id,text,order_index,required,source) VALUES(?,?,?,?,?)',(int(p['checklist_id']),p['text'],int(order),1 if p.get('required',True) else 0,p.get('source','')))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='checklist_item_update':
                f=[];a=[]
                for k in ('text','order_index','source'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                if 'required' in p:f.append('required=?');a.append(1 if p['required'] else 0)
                a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE checklist_items SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='checklist_item_remove':
                with self._connect() as c:cur=c.execute('DELETE FROM checklist_items WHERE id=?',(int(p['id']),))
                return {'ok':True,'removed':cur.rowcount}

            if operation=='learner_create':
                with self._connect() as c:cur=c.execute('INSERT INTO learners(alias,role,notes,status,created_at,updated_at) VALUES(?,?,?,?,?,?)',(p['alias'],p.get('role',''),p.get('notes',''),p.get('status','active'),now,now))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='learner_list':return self._list('learners',p.get('status'),p.get('limit',200),'alias')
            if operation=='learner_get':return self._get('learners',p['id'])
            if operation=='learner_update':
                f=[];a=[]
                for k in ('alias','role','notes','status'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                f.append('updated_at=?');a.append(now);a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE learners SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='progress_set':
                status=p.get('status','completed');completed=now if status=='completed' else None
                with self._connect() as c:c.execute('''INSERT INTO progress(learner_id,item_type,item_id,status,score,completed_at,notes,updated_at) VALUES(?,?,?,?,?,?,?,?)
                    ON CONFLICT(learner_id,item_type,item_id) DO UPDATE SET status=excluded.status,score=excluded.score,completed_at=excluded.completed_at,notes=excluded.notes,updated_at=excluded.updated_at''',(int(p['learner_id']),p['item_type'],int(p['item_id']),status,p.get('score'),completed,p.get('notes',''),now))
                return {'ok':True}
            if operation=='progress_get':
                with self._connect() as c:rows=c.execute('SELECT * FROM progress WHERE learner_id=? ORDER BY updated_at DESC',(int(p['learner_id']),)).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}
            if operation=='progress_summary':
                with self._connect() as c:
                    rows=c.execute('SELECT status,COUNT(*) n,AVG(score) avg_score FROM progress WHERE learner_id=? GROUP BY status',(int(p['learner_id']),)).fetchall()
                return {'ok':True,'items':self._rows(rows)}

            if operation=='scenario_create':
                with self._connect() as c:cur=c.execute('INSERT INTO scenarios(title,role,prompt,expected_points,source,difficulty,status,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(p['title'],p.get('role',''),p['prompt'],p.get('expected_points',''),p.get('source',''),p.get('difficulty','normal'),p.get('status','active'),now,now))
                return {'ok':True,'id':cur.lastrowid}
            if operation=='scenario_list':return self._list('scenarios',p.get('status'),p.get('limit',200),'updated_at DESC')
            if operation=='scenario_get':return self._get('scenarios',p['id'])
            if operation=='scenario_search':
                q=f"%{p['query']}%"
                with self._connect() as c:rows=c.execute('SELECT * FROM scenarios WHERE title LIKE ? OR prompt LIKE ? OR expected_points LIKE ? OR role LIKE ? ORDER BY updated_at DESC LIMIT ?',(q,q,q,q,int(p.get('limit',100)))).fetchall()
                return {'ok':True,'items':self._rows(rows),'count':len(rows)}
            if operation=='scenario_update':
                f=[];a=[]
                for k in ('title','role','prompt','expected_points','source','difficulty','status'):
                    if k in p and p[k] is not None:f.append(f'{k}=?');a.append(p[k])
                f.append('updated_at=?');a.append(now);a.append(int(p['id']))
                with self._connect() as c:cur=c.execute(f"UPDATE scenarios SET {', '.join(f)} WHERE id=?",a)
                return {'ok':True,'updated':cur.rowcount}
            if operation=='scenario_archive':return self.execute('scenario_update',id=p['id'],status='archived')

            if operation=='role_dashboard':
                role=str(p.get('role',''))
                with self._connect() as c:
                    tracks=c.execute("SELECT * FROM tracks WHERE status='active' AND (role=? OR role='') ORDER BY name",(role,)).fetchall()
                    checks=c.execute("SELECT * FROM checklists WHERE status='active' AND (role=? OR role='') ORDER BY name",(role,)).fetchall()
                    quizzes=c.execute("SELECT * FROM quizzes WHERE status='active' AND (role=? OR role='') ORDER BY name",(role,)).fetchall()
                    scenarios=c.execute("SELECT * FROM scenarios WHERE status='active' AND (role=? OR role='') ORDER BY title",(role,)).fetchall()
                return {'ok':True,'role':role,'tracks':self._rows(tracks),'checklists':self._rows(checks),'quizzes':self._rows(quizzes),'scenarios':self._rows(scenarios)}
            if operation=='stats':
                with self._connect() as c:
                    tables=['tracks','modules','quizzes','questions','checklists','checklist_items','learners','progress','scenarios']
                    d={t:c.execute(f'SELECT COUNT(*) n FROM {t}').fetchone()['n'] for t in tables}
                return {'ok':True,**d}

            return {'ok':False,'error':f'Operação de treinamento desconhecida: {operation}'}
        except sqlite3.IntegrityError as exc:return {'ok':False,'error':f'Conflito de dados: {exc}'}
        except Exception as exc:return {'ok':False,'error':str(exc)}
