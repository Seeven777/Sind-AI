from __future__ import annotations

from dataclasses import dataclass,field
from datetime import datetime,timezone,timedelta
import json
from uuid import uuid4


def now():
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ScheduledJob:
    job_id:str
    name:str
    kind:str
    schedule:str|None=None
    status:str='enabled'
    next_run_at:str|None=None
    payload:dict=field(default_factory=dict)


class SchedulerRepository:
    def __init__(self,conn):
        self.conn=conn

    def create_interval(self,name,kind,minutes,payload=None):
        job_id=str(uuid4()); ts=now()
        next_run=(datetime.now(timezone.utc)+timedelta(minutes=int(minutes))).isoformat()
        self.conn.execute(
            """INSERT INTO scheduled_jobs(
               job_id,name,kind,schedule,status,next_run_at,payload_json,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                job_id,name,kind,f'interval:{int(minutes)}m','enabled',next_run,
                json.dumps(payload or {},ensure_ascii=False),ts,ts
            )
        ); self.conn.commit()
        return job_id

    def create_once(self,name,kind,run_at,payload=None):
        job_id=str(uuid4());ts=now()
        self.conn.execute(
            """INSERT INTO scheduled_jobs(
               job_id,name,kind,schedule,status,next_run_at,payload_json,created_at,updated_at
               ) VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                job_id,name,kind,'once','enabled',str(run_at),
                json.dumps(payload or {},ensure_ascii=False),ts,ts
            )
        );self.conn.commit()
        return job_id

    def disable(self,job_id):
        self.conn.execute(
            "UPDATE scheduled_jobs SET status='disabled',next_run_at=NULL,updated_at=? WHERE job_id=?",
            (now(),job_id)
        );self.conn.commit()

    def due(self,at_iso=None,limit=50):
        at_iso=at_iso or now()
        rows=self.conn.execute(
            """SELECT * FROM scheduled_jobs
               WHERE status='enabled' AND next_run_at IS NOT NULL AND next_run_at<=?
               ORDER BY next_run_at LIMIT ?""",
            (at_iso,limit)
        ).fetchall()
        return [self._row(r) for r in rows]

    def all(self):
        return [self._row(r) for r in self.conn.execute(
            'SELECT * FROM scheduled_jobs ORDER BY created_at'
        ).fetchall()]

    def reschedule(self,job_id,minutes):
        next_run=(datetime.now(timezone.utc)+timedelta(minutes=int(minutes))).isoformat()
        self.conn.execute(
            'UPDATE scheduled_jobs SET next_run_at=?,updated_at=? WHERE job_id=?',
            (next_run,now(),job_id)
        ); self.conn.commit()

    def _row(self,row):
        x=dict(row)
        try:x['payload']=json.loads(x.pop('payload_json') or '{}')
        except Exception:x['payload']={}
        return x


class Scheduler:
    def __init__(self,*,repository,connectors,watchers,bus):
        self.repository=repository
        self.connectors=connectors
        self.watchers=watchers
        self.bus=bus
        self.enabled=True

    async def run_due(self):
        results=[]
        for job in self.repository.due():
            kind=job['kind']
            payload=job.get('payload') or {}
            try:
                if kind=='connector.sync_all':
                    output=await self.connectors.sync_all()
                elif kind=='watchers.check':
                    output=await self.watchers.check_all()
                elif kind=='reminder':
                    output={'message':payload.get('message','Lembrete')}
                    await self.bus.publish(__import__('jarvis.core.events',fromlist=['Event']).Event(
                        'reminder.due',severity='warning',
                        payload={'job_id':job['job_id'],'message':output['message']}
                    ))
                else:
                    output={'status':'skipped','reason':f'unknown job kind: {kind}'}

                if job.get('schedule')=='once':
                    self.repository.disable(job['job_id'])
                else:
                    minutes=self._interval_minutes(job.get('schedule'))
                    self.repository.reschedule(job['job_id'],minutes)
                await self.bus.publish(__import__('jarvis.core.events',fromlist=['Event']).Event(
                    'scheduler.job.completed',
                    payload={'job_id':job['job_id'],'kind':kind}
                ))
                results.append({'job_id':job['job_id'],'kind':kind,'status':'completed','output':output})
            except Exception as exc:
                await self.bus.publish(__import__('jarvis.core.events',fromlist=['Event']).Event(
                    'scheduler.job.failed',severity='error',
                    payload={'job_id':job['job_id'],'kind':kind,'error':str(exc)}
                ))
                results.append({'job_id':job['job_id'],'kind':kind,'status':'failed','error':str(exc)})
        return results

    def ensure_defaults(self):
        kinds={j['kind'] for j in self.repository.all()}
        if 'connector.sync_all' not in kinds:
            self.repository.create_interval('Sincronizar connectors','connector.sync_all',5)
        if 'watchers.check' not in kinds:
            self.repository.create_interval('Verificar watchers','watchers.check',2)

    def _interval_minutes(self,schedule):
        try:
            return max(1,int(str(schedule).split(':',1)[1].rstrip('m')))
        except Exception:
            return 5
