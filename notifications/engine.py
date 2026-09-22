import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


class NotificationEngine:
    def __init__(self, db_path):
        self.db_path=Path(db_path);self.db_path.parent.mkdir(parents=True,exist_ok=True);self._init_db()
    def _connect(self):
        c=sqlite3.connect(self.db_path,timeout=20);c.row_factory=sqlite3.Row;return c
    def _now(self):return datetime.now().isoformat(timespec='seconds')
    def _init_db(self):
        with self._connect() as c:
            c.executescript('''
            CREATE TABLE IF NOT EXISTS notifications(
              id INTEGER PRIMARY KEY AUTOINCREMENT,created_at TEXT NOT NULL,
              title TEXT NOT NULL,message TEXT NOT NULL,category TEXT DEFAULT 'general',
              severity TEXT DEFAULT 'info',source TEXT DEFAULT '',source_id TEXT DEFAULT '',
              status TEXT NOT NULL DEFAULT 'unread',payload_json TEXT NOT NULL DEFAULT '{}',
              read_at TEXT,dismissed_at TEXT);
            CREATE INDEX IF NOT EXISTS idx_notifications_status ON notifications(status,id DESC);
            ''')
    def _row(self,r):
        if not r:return None
        d=dict(r)
        try:d['payload']=json.loads(d.pop('payload_json') or '{}')
        except Exception:d['payload']={}
        return d
    def _rows(self,rows):return [self._row(r) for r in rows]
    def add(self,title,message,category='general',severity='info',source='',source_id='',payload=None):
        with self._connect() as c:
            cur=c.execute('''INSERT INTO notifications(created_at,title,message,category,severity,source,source_id,status,payload_json)
                             VALUES(?,?,?,?,?,?,?,?,?)''',(self._now(),str(title),str(message),str(category),str(severity),str(source),str(source_id),'unread',json.dumps(payload or {},ensure_ascii=False,default=str)))
        return self.get(cur.lastrowid)
    def get(self,id):
        with self._connect() as c:r=c.execute('SELECT * FROM notifications WHERE id=?',(int(id),)).fetchone()
        return {'ok':bool(r),'data':self._row(r),'error':None if r else 'Notificação não encontrada.'}
    def list(self,status=None,category=None,severity=None,limit=200):
        sql='SELECT * FROM notifications WHERE 1=1';args=[]
        if status:sql+=' AND status=?';args.append(str(status))
        if category:sql+=' AND category=?';args.append(str(category))
        if severity:sql+=' AND severity=?';args.append(str(severity))
        sql+=' ORDER BY id DESC LIMIT ?';args.append(int(limit))
        with self._connect() as c:rows=c.execute(sql,args).fetchall()
        return {'ok':True,'items':self._rows(rows),'count':len(rows)}
    def unread(self,limit=200):return self.list(status='unread',limit=limit)
    def mark_read(self,id):
        with self._connect() as c:cur=c.execute("UPDATE notifications SET status='read',read_at=? WHERE id=?",(self._now(),int(id)))
        return {'ok':cur.rowcount>0,'id':int(id)}
    def mark_unread(self,id):
        with self._connect() as c:cur=c.execute("UPDATE notifications SET status='unread',read_at=NULL WHERE id=?",(int(id),))
        return {'ok':cur.rowcount>0,'id':int(id)}
    def mark_all_read(self):
        with self._connect() as c:cur=c.execute("UPDATE notifications SET status='read',read_at=? WHERE status='unread'",(self._now(),))
        return {'ok':True,'updated':cur.rowcount}
    def dismiss(self,id):
        with self._connect() as c:cur=c.execute("UPDATE notifications SET status='dismissed',dismissed_at=? WHERE id=?",(self._now(),int(id)))
        return {'ok':cur.rowcount>0,'id':int(id)}
    def delete(self,id):
        with self._connect() as c:cur=c.execute('DELETE FROM notifications WHERE id=?',(int(id),))
        return {'ok':cur.rowcount>0,'id':int(id)}
    def clear(self,status='dismissed',older_than_days=None):
        sql='DELETE FROM notifications WHERE status=?';args=[str(status)]
        if older_than_days is not None:
            cutoff=(datetime.now()-timedelta(days=float(older_than_days))).isoformat(timespec='seconds')
            sql+=' AND created_at<?';args.append(cutoff)
        with self._connect() as c:cur=c.execute(sql,args)
        return {'ok':True,'removed':cur.rowcount}
    def search(self,query,limit=100):
        q=f"%{str(query).strip()}%"
        with self._connect() as c:rows=c.execute('''SELECT * FROM notifications WHERE title LIKE ? OR message LIKE ? OR source LIKE ? OR category LIKE ? ORDER BY id DESC LIMIT ?''',(q,q,q,q,int(limit))).fetchall()
        return {'ok':True,'items':self._rows(rows),'count':len(rows)}
    def stats(self):
        with self._connect() as c:
            total=c.execute('SELECT COUNT(*) n FROM notifications').fetchone()['n']
            rows=c.execute('SELECT status,COUNT(*) n FROM notifications GROUP BY status').fetchall()
            cats=c.execute("SELECT category,COUNT(*) n FROM notifications WHERE status='unread' GROUP BY category").fetchall()
        return {'ok':True,'notifications':total,'statuses':{r['status']:r['n'] for r in rows},'unread_by_category':{r['category']:r['n'] for r in cats}}
    def export(self,path,limit=10000):
        out=Path(path).expanduser().resolve();out.parent.mkdir(parents=True,exist_ok=True)
        data=self.list(limit=limit)['items'];out.write_text(json.dumps(data,indent=2,ensure_ascii=False,default=str),encoding='utf-8')
        return {'ok':True,'path':str(out),'notifications':len(data)}
    def execute(self,operation,**params):
        mapping={'add':self.add,'get':self.get,'list':self.list,'unread':self.unread,'mark_read':self.mark_read,
                 'mark_unread':self.mark_unread,'mark_all_read':self.mark_all_read,'dismiss':self.dismiss,'delete':self.delete,
                 'clear':self.clear,'search':self.search,'stats':self.stats,'export':self.export}
        fn=mapping.get(operation)
        if not fn:return {'ok':False,'error':f'Operação de notificação desconhecida: {operation}'}
        return fn(**params)
