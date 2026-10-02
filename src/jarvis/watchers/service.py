from __future__ import annotations

import json
from datetime import datetime,timezone,timedelta
from uuid import uuid4

from jarvis.core.events import Event


def now():
    return datetime.now(timezone.utc).isoformat()


class WatcherRepository:
    def __init__(self,conn):
        self.conn=conn

    def ensure(self,name,kind,config):
        row=self.conn.execute(
            'SELECT watcher_id FROM watchers WHERE name=? AND kind=?',(name,kind)
        ).fetchone()
        if row:return row['watcher_id']
        wid=str(uuid4()); ts=now()
        self.conn.execute(
            """INSERT INTO watchers(
               watcher_id,name,kind,status,config_json,state_json,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?)""",
            (wid,name,kind,'enabled',json.dumps(config,ensure_ascii=False),'{}',ts,ts)
        ); self.conn.commit()
        return wid

    def enabled(self):
        rows=self.conn.execute(
            "SELECT * FROM watchers WHERE status='enabled' ORDER BY created_at"
        ).fetchall()
        return [self._row(r) for r in rows]

    def update_state(self,watcher_id,state,triggered=False):
        self.conn.execute(
            """UPDATE watchers SET state_json=?,updated_at=?,last_checked_at=?,
               last_triggered_at=CASE WHEN ? THEN ? ELSE last_triggered_at END
               WHERE watcher_id=?""",
            (
                json.dumps(state,ensure_ascii=False),now(),now(),
                1 if triggered else 0,now(),watcher_id
            )
        ); self.conn.commit()

    def _row(self,row):
        x=dict(row)
        for key in ('config_json','state_json'):
            try:x[key[:-5]]=json.loads(x.pop(key) or '{}')
            except Exception:x[key[:-5]]={}
        return x


class WatcherService:
    def __init__(self,*,repository,connector_repository,bus):
        self.repository=repository
        self.connector_repository=connector_repository
        self.bus=bus

    def ensure_defaults(self):
        self.repository.ensure(
            'Novos itens importantes','connector.priority',
            {'min_priority':80}
        )
        self.repository.ensure(
            'Agenda próxima','calendar.upcoming',
            {'within_minutes':180}
        )

    async def check_all(self):
        results=[]
        for watcher in self.repository.enabled():
            if watcher['kind']=='connector.priority':
                result=await self._check_priority(watcher)
            elif watcher['kind']=='calendar.upcoming':
                result=await self._check_calendar(watcher)
            elif watcher['kind']=='file.changed':
                result=await self._check_file_changed(watcher)
            else:
                result={'watcher_id':watcher['watcher_id'],'triggered':False,'reason':'unknown kind'}
            results.append(result)
        return results

    async def _check_priority(self,watcher):
        min_priority=int((watcher.get('config') or {}).get('min_priority',80))
        items=[
            i for i in self.connector_repository.unread(limit=20)
            if int(i.get('priority') or 0)>=min_priority
        ]
        previous=set((watcher.get('state') or {}).get('seen_item_ids',[]))
        new=[i for i in items if i['item_id'] not in previous]
        seen=list((previous|{i['item_id'] for i in items}))[-200:]
        self.repository.update_state(
            watcher['watcher_id'],{'seen_item_ids':seen},triggered=bool(new)
        )
        for item in new:
            await self.bus.publish(Event(
                'watcher.triggered',severity='warning',
                payload={
                    'watcher_id':watcher['watcher_id'],'kind':watcher['kind'],
                    'item_id':item['item_id'],'title':item['title'],'priority':item['priority']
                }
            ))
        return {
            'watcher_id':watcher['watcher_id'],'kind':watcher['kind'],
            'triggered':bool(new),'new_items':len(new)
        }

    async def _check_file_changed(self,watcher):
        from pathlib import Path
        import hashlib
        path=Path((watcher.get('config') or {}).get('path','')).expanduser()
        previous=(watcher.get('state') or {}).get('fingerprint')
        fingerprint=None
        exists=path.is_file()
        if exists:
            stat=path.stat()
            fingerprint=hashlib.sha256(
                f'{stat.st_size}|{stat.st_mtime_ns}'.encode('utf-8')
            ).hexdigest()
        triggered=previous is not None and fingerprint!=previous
        self.repository.update_state(
            watcher['watcher_id'],
            {'fingerprint':fingerprint,'exists':exists,'path':str(path)},
            triggered=triggered
        )
        if triggered:
            await self.bus.publish(Event(
                'watcher.triggered',severity='warning',
                payload={
                    'watcher_id':watcher['watcher_id'],'kind':watcher['kind'],
                    'path':str(path),'exists':exists
                }
            ))
        return {
            'watcher_id':watcher['watcher_id'],'kind':watcher['kind'],
            'triggered':triggered,'path':str(path),'exists':exists
        }

    async def _check_calendar(self,watcher):
        within=int((watcher.get('config') or {}).get('within_minutes',180))
        now_dt=datetime.now(timezone.utc)
        events=self.connector_repository.upcoming_events(now_dt.isoformat(),limit=20)
        near=[]
        for event in events:
            try:
                dt=datetime.fromisoformat(event['occurred_at'])
            except Exception:
                continue
            if dt<=now_dt+timedelta(minutes=within):
                near.append(event)
        previous=set((watcher.get('state') or {}).get('seen_event_ids',[]))
        new=[e for e in near if e['item_id'] not in previous]
        seen=list((previous|{e['item_id'] for e in near}))[-200:]
        self.repository.update_state(
            watcher['watcher_id'],{'seen_event_ids':seen},triggered=bool(new)
        )
        for event in new:
            await self.bus.publish(Event(
                'watcher.triggered',severity='warning',
                payload={
                    'watcher_id':watcher['watcher_id'],'kind':watcher['kind'],
                    'item_id':event['item_id'],'title':event['title'],
                    'occurred_at':event['occurred_at']
                }
            ))
        return {
            'watcher_id':watcher['watcher_id'],'kind':watcher['kind'],
            'triggered':bool(new),'events':len(new)
        }
