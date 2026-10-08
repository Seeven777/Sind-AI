from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


class ConnectorRepository:
    def __init__(self,conn):
        self.conn=conn

    def register_source(self,connector,config=None):
        ts=now()
        self.conn.execute(
            """INSERT INTO connector_sources(
                connector_id,kind,name,status,read_only,config_json,created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(connector_id) DO UPDATE SET
                kind=excluded.kind,name=excluded.name,status=excluded.status,
                read_only=excluded.read_only,config_json=excluded.config_json,
                updated_at=excluded.updated_at""",
            (
                connector.connector_id,connector.connector_kind,connector.name,
                'configured',1 if connector.read_only else 0,
                json.dumps(config or {},ensure_ascii=False),ts,ts
            )
        ); self.conn.commit()


    def set_source_status(self,connector_id,status,error=None):
        self.conn.execute(
            'UPDATE connector_sources SET status=?,last_error=?,updated_at=? WHERE connector_id=?',
            (status,error,now(),connector_id)
        )
        self.conn.commit()

    def start_sync(self,connector_id):
        sync_id=str(uuid4())
        self.conn.execute(
            'INSERT INTO connector_sync_runs(sync_id,connector_id,status,started_at) VALUES(?,?,?,?)',
            (sync_id,connector_id,'running',now())
        ); self.conn.commit()
        return sync_id

    def finish_sync(self,sync_id,connector_id,*,discovered,stored,error=None):
        status='failed' if error else 'completed'
        self.conn.execute(
            'UPDATE connector_sync_runs SET status=?,ended_at=?,discovered=?,stored=?,error=? WHERE sync_id=?',
            (status,now(),discovered,stored,error,sync_id)
        )
        self.conn.execute(
            'UPDATE connector_sources SET status=?,last_sync_at=?,last_error=?,updated_at=? WHERE connector_id=?',
            ('error' if error else 'healthy',now(),error,now(),connector_id)
        )
        self.conn.commit()

    def upsert_item(self,connector_id,item):
        row=self.conn.execute(
            'SELECT item_id FROM connector_items WHERE connector_id=? AND external_id=?',
            (connector_id,item.external_id)
        ).fetchone()
        if row:
            self.conn.execute(
                """UPDATE connector_items SET
                   item_type=?,title=?,content=?,occurred_at=?,source_uri=?,priority=?,metadata_json=?
                   WHERE item_id=?""",
                (
                    item.item_type,item.title,item.content,item.occurred_at,item.source_uri,
                    int(item.priority),json.dumps(item.metadata,ensure_ascii=False),row['item_id']
                )
            ); self.conn.commit()
            return row['item_id'],False
        item_id=str(uuid4())
        self.conn.execute(
            """INSERT INTO connector_items(
                item_id,connector_id,external_id,item_type,title,content,occurred_at,
                received_at,source_uri,priority,is_read,metadata_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,0,?)""",
            (
                item_id,connector_id,item.external_id,item.item_type,item.title,item.content,
                item.occurred_at,now(),item.source_uri,int(item.priority),
                json.dumps(item.metadata,ensure_ascii=False)
            )
        ); self.conn.commit()
        return item_id,True

    def unread(self,limit=30,item_type=None):
        sql="SELECT * FROM connector_items WHERE is_read=0"
        params=[]
        if item_type:
            sql+=" AND item_type=?"; params.append(item_type)
        sql+=" ORDER BY priority DESC, COALESCE(occurred_at,received_at) DESC LIMIT ?"
        params.append(limit)
        return [self._item(r) for r in self.conn.execute(sql,params).fetchall()]

    def upcoming_events(self,now_iso,limit=10):
        return [self._item(r) for r in self.conn.execute(
            """SELECT * FROM connector_items
               WHERE item_type='calendar_event' AND occurred_at IS NOT NULL AND occurred_at>=?
               ORDER BY occurred_at LIMIT ?""",
            (now_iso,limit)
        ).fetchall()]

    def recent(self,limit=30):
        return [self._item(r) for r in self.conn.execute(
            'SELECT * FROM connector_items ORDER BY received_at DESC LIMIT ?',(limit,)
        ).fetchall()]

    def by_connector(self,connector_id,limit=50,item_type=None):
        sql='SELECT * FROM connector_items WHERE connector_id=?'
        params=[connector_id]
        if item_type:
            sql+=' AND item_type=?';params.append(item_type)
        sql+=' ORDER BY priority DESC, COALESCE(occurred_at,received_at) ASC LIMIT ?'
        params.append(limit)
        return [self._item(r) for r in self.conn.execute(sql,params).fetchall()]

    def mark_read(self,item_id):
        self.conn.execute('UPDATE connector_items SET is_read=1 WHERE item_id=?',(item_id,))
        self.conn.commit()

    def sources(self):
        rows=self.conn.execute('SELECT * FROM connector_sources ORDER BY name').fetchall()
        result=[]
        for r in rows:
            x=dict(r)
            try:x['config']=json.loads(x.pop('config_json') or '{}')
            except Exception:x['config']={}
            result.append(x)
        return result

    def counts(self):
        row=self.conn.execute(
            """SELECT
               COUNT(*) total,
               SUM(CASE WHEN is_read=0 THEN 1 ELSE 0 END) unread,
               SUM(CASE WHEN item_type='calendar_event' THEN 1 ELSE 0 END) events
               FROM connector_items"""
        ).fetchone()
        return {k:int(row[k] or 0) for k in ('total','unread','events')}

    def _item(self,row):
        x=dict(row)
        try:x['metadata']=json.loads(x.pop('metadata_json') or '{}')
        except Exception:x['metadata']={}
        x['is_read']=bool(x.get('is_read'))
        return x
