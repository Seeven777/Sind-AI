import hashlib
import json
import math
import sqlite3
from datetime import datetime
from pathlib import Path

import requests

class SemanticMemory:
    """Memória vetorial opcional usando embeddings do Ollama.

    É desligada por padrão para manter o Jarvis leve em qualquer máquina.
    Quando habilitada, respostas não dependem dela: falhas degradam para FTS5.
    """
    def __init__(self, db_path, ollama_url, model, enabled=False):
        self.db_path=Path(db_path);self.db_path.parent.mkdir(parents=True,exist_ok=True)
        raw_url=str(ollama_url).rstrip('/')
        # Config legado pode apontar diretamente para /api/chat; embeddings/tags precisam da base Ollama.
        for suffix in ('/api/chat','/api/generate','/api/embed','/api/embeddings'):
            if raw_url.endswith(suffix):
                raw_url=raw_url[:-len(suffix)]
                break
        self.ollama_url=raw_url;self.model=str(model);self.enabled=bool(enabled)
        self._availability_cache=None;self._init_db()
    def _connect(self):
        c=sqlite3.connect(self.db_path,timeout=20);c.row_factory=sqlite3.Row;return c
    def _now(self):return datetime.now().isoformat(timespec='seconds')
    def _init_db(self):
        with self._connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS semantic_items(
              id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,kind TEXT NOT NULL,
              text TEXT NOT NULL,text_hash TEXT NOT NULL UNIQUE,metadata_json TEXT NOT NULL DEFAULT '{}',
              embedding_json TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS idx_semantic_kind ON semantic_items(kind,id DESC);
            ''')
    def available(self,refresh=False):
        if not self.enabled:return False
        if self._availability_cache is not None and not refresh:return self._availability_cache
        try:
            r=requests.get(self.ollama_url+'/api/tags',timeout=2);r.raise_for_status();models=r.json().get('models',[])
            names={str(x.get('name','')).split(':')[0] for x in models}|{str(x.get('model','')).split(':')[0] for x in models}
            self._availability_cache=self.model.split(':')[0] in names
        except Exception:self._availability_cache=False
        return self._availability_cache
    def _embed(self,text):
        if not self.available():return None
        r=requests.post(self.ollama_url+'/api/embed',json={'model':self.model,'input':str(text)},timeout=30);r.raise_for_status();data=r.json();emb=data.get('embeddings') or []
        return emb[0] if emb and isinstance(emb[0],list) else None
    def remember(self,kind,text,metadata=None):
        text=' '.join(str(text or '').split())[:12000]
        if not text or not self.enabled:return {'ok':True,'stored':False,'reason':'disabled_or_empty'}
        h=hashlib.sha256(text.encode('utf-8')).hexdigest()
        with self._connect() as c:
            if c.execute('SELECT id FROM semantic_items WHERE text_hash=?',(h,)).fetchone():return {'ok':True,'stored':False,'reason':'duplicate'}
        vector=self._embed(text)
        if not vector:return {'ok':False,'stored':False,'error':'Embedding model indisponível.'}
        with self._connect() as c:
            cur=c.execute('INSERT INTO semantic_items(created_at,kind,text,text_hash,metadata_json,embedding_json) VALUES(?,?,?,?,?,?)',(self._now(),str(kind),text,h,json.dumps(metadata or {},ensure_ascii=False,default=str),json.dumps(vector)))
        return {'ok':True,'stored':True,'id':int(cur.lastrowid)}
    def _cosine(self,a,b):
        if not a or not b or len(a)!=len(b):return -1.0
        dot=sum(x*y for x,y in zip(a,b));na=math.sqrt(sum(x*x for x in a));nb=math.sqrt(sum(y*y for y in b));return dot/(na*nb) if na and nb else -1.0
    def search(self,query,limit=4,max_candidates=1000):
        if not self.enabled:return {'ok':True,'items':[],'count':0,'enabled':False}
        qv=self._embed(query)
        if not qv:return {'ok':False,'items':[],'count':0,'error':'Embedding model indisponível.'}
        with self._connect() as c:rows=c.execute('SELECT * FROM semantic_items ORDER BY id DESC LIMIT ?',(int(max_candidates),)).fetchall()
        scored=[]
        for r in rows:
            try:v=json.loads(r['embedding_json']);score=self._cosine(qv,v)
            except Exception:continue
            d=dict(r);d.pop('embedding_json',None);d['score']=round(score,5)
            try:d['metadata']=json.loads(d.pop('metadata_json') or '{}')
            except Exception:d['metadata']={}
            scored.append((score,d))
        scored.sort(key=lambda x:-x[0]);items=[x[1] for x in scored[:int(limit)]]
        return {'ok':True,'items':items,'count':len(items),'enabled':True}
    def stats(self):
        with self._connect() as c:n=c.execute('SELECT COUNT(*) n FROM semantic_items').fetchone()['n']
        return {'ok':True,'enabled':self.enabled,'available':self.available() if self.enabled else False,'items':n,'model':self.model}
