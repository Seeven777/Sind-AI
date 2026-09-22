import json
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path


class AutomationEngine:
    """
    Scheduler local persistente e leve.

    Tipos de agenda:
    - once: run_at ISO local
    - interval: interval_seconds
    - daily: hour/minute
    - weekly: weekday 0=segunda ... 6=domingo + hour/minute

    O executor é injetado pelo JarvisAgent. Assim o scheduler não conhece
    diretamente ActionHub, WorkflowHub ou Skills.
    """

    def __init__(self, db_path, poll_seconds=5):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.poll_seconds = max(2, int(poll_seconds))
        self._executor = None
        self._approval_callback = None
        self._notifier = None
        self._stop = threading.Event()
        self._thread = None
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=20)
        conn.row_factory = sqlite3.Row
        return conn

    def _now(self):
        return datetime.now()

    def _iso(self, dt=None):
        return (dt or self._now()).isoformat(timespec="seconds")

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS automation_jobs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                schedule_type TEXT NOT NULL,
                schedule_json TEXT NOT NULL DEFAULT '{}',
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL,
                params_json TEXT NOT NULL DEFAULT '{}',
                status TEXT NOT NULL DEFAULT 'enabled',
                next_run TEXT,
                last_run TEXT,
                last_status TEXT,
                last_error TEXT,
                run_count INTEGER NOT NULL DEFAULT 0,
                failure_count INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 2,
                retry_backoff_seconds INTEGER NOT NULL DEFAULT 60,
                tags TEXT DEFAULT '',
                require_confirmation INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_automation_next
            ON automation_jobs(status,next_run);

            CREATE TABLE IF NOT EXISTS automation_runs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                result_json TEXT NOT NULL DEFAULT '{}',
                error TEXT,
                attempt INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(job_id) REFERENCES automation_jobs(id)
            );
            CREATE INDEX IF NOT EXISTS idx_automation_runs_job
            ON automation_runs(job_id,id DESC);
            """)

    def set_executor(self, callback):
        self._executor = callback
        return {"ok": True}

    def set_approval_callback(self, callback):
        self._approval_callback = callback
        return {"ok": True}

    def set_notifier(self, callback):
        self._notifier = callback
        return {"ok": True}

    def _row(self, row):
        if not row:
            return None
        d = dict(row)
        for src, dst in [("schedule_json","schedule"),("params_json","params")]:
            try:
                d[dst] = json.loads(d.pop(src) or "{}")
            except Exception:
                d[dst] = {}
        d["require_confirmation"] = bool(d.get("require_confirmation"))
        d["tags"] = [x.strip() for x in (d.get("tags") or "").split(",") if x.strip()]
        return d

    def _rows(self, rows):
        return [self._row(r) for r in rows]

    def _compute_next(self, schedule_type, schedule, after=None):
        now = after or self._now()
        st = str(schedule_type).lower().strip()
        schedule = dict(schedule or {})

        if st == "once":
            raw = schedule.get("run_at")
            if not raw:
                raise ValueError("Agenda once requer run_at.")
            return datetime.fromisoformat(str(raw))

        if st == "interval":
            seconds = int(schedule.get("interval_seconds", 0))
            if seconds < 5:
                raise ValueError("Intervalo mínimo: 5 segundos.")
            return now + timedelta(seconds=seconds)

        if st == "daily":
            hour = int(schedule.get("hour", 8))
            minute = int(schedule.get("minute", 0))
            candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if candidate <= now:
                candidate += timedelta(days=1)
            return candidate

        if st == "weekly":
            weekday = int(schedule.get("weekday", 0))
            hour = int(schedule.get("hour", 8))
            minute = int(schedule.get("minute", 0))
            if weekday < 0 or weekday > 6:
                raise ValueError("weekday deve estar entre 0 e 6.")
            delta = (weekday - now.weekday()) % 7
            candidate = (now + timedelta(days=delta)).replace(
                hour=hour, minute=minute, second=0, microsecond=0
            )
            if candidate <= now:
                candidate += timedelta(days=7)
            return candidate

        raise ValueError(f"Tipo de agenda não suportado: {schedule_type}")

    def create(self, name, schedule_type, target_type, target_id, schedule=None,
               params=None, description="", max_retries=2, retry_backoff_seconds=60,
               tags=None, require_confirmation=False, enabled=True):
        now = self._iso()
        try:
            next_run = self._compute_next(schedule_type, schedule or {})
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        status = "enabled" if enabled else "disabled"
        try:
            with self._connect() as conn:
                cur = conn.execute(
                    """INSERT INTO automation_jobs(
                       name,description,schedule_type,schedule_json,target_type,target_id,
                       params_json,status,next_run,max_retries,retry_backoff_seconds,tags,
                       require_confirmation,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        str(name).strip(), str(description), str(schedule_type).lower(),
                        json.dumps(schedule or {}, ensure_ascii=False),
                        str(target_type).lower(), str(target_id),
                        json.dumps(params or {}, ensure_ascii=False),
                        status, self._iso(next_run), int(max_retries),
                        int(retry_backoff_seconds),
                        ",".join(tags or []) if isinstance(tags, list) else str(tags or ""),
                        1 if require_confirmation else 0, now, now,
                    )
                )
                job_id = int(cur.lastrowid)
        except sqlite3.IntegrityError:
            return {"ok": False, "error": f"Já existe uma automação chamada '{name}'."}
        return self.get(job_id)

    def list(self, status=None, target_type=None, tag=None, limit=200):
        sql = "SELECT * FROM automation_jobs WHERE 1=1"
        args = []
        if status:
            sql += " AND status=?"; args.append(str(status))
        if target_type:
            sql += " AND target_type=?"; args.append(str(target_type))
        if tag:
            sql += " AND (','||tags||',') LIKE ?"; args.append(f"%,{tag},%")
        sql += " ORDER BY COALESCE(next_run,'9999') ASC,id DESC LIMIT ?"
        args.append(int(limit))
        with self._connect() as conn:
            rows = conn.execute(sql, args).fetchall()
        return {"ok": True, "items": self._rows(rows), "count": len(rows)}

    def get(self, job_id=None, name=None):
        with self._connect() as conn:
            if job_id is not None:
                row = conn.execute("SELECT * FROM automation_jobs WHERE id=?", (int(job_id),)).fetchone()
            else:
                row = conn.execute("SELECT * FROM automation_jobs WHERE name=?", (str(name),)).fetchone()
        return {"ok": bool(row), "data": self._row(row), "error": None if row else "Automação não encontrada."}

    def update(self, job_id, **fields):
        allowed = {
            "name","description","target_type","target_id","max_retries",
            "retry_backoff_seconds","require_confirmation"
        }
        sets=[]; args=[]
        for k,v in fields.items():
            if k in allowed and v is not None:
                if k=="require_confirmation":
                    v=1 if v else 0
                sets.append(f"{k}=?");args.append(v)

        if "params" in fields and fields["params"] is not None:
            sets.append("params_json=?");args.append(json.dumps(fields["params"],ensure_ascii=False))
        if "tags" in fields and fields["tags"] is not None:
            tags=fields["tags"]
            sets.append("tags=?");args.append(",".join(tags) if isinstance(tags,list) else str(tags))
        if "schedule_type" in fields or "schedule" in fields:
            current=self.get(job_id).get("data")
            if not current:
                return {"ok":False,"error":"Automação não encontrada."}
            st=fields.get("schedule_type",current["schedule_type"])
            sc=fields.get("schedule",current["schedule"])
            try:nxt=self._compute_next(st,sc)
            except Exception as exc:return {"ok":False,"error":str(exc)}
            sets += ["schedule_type=?","schedule_json=?","next_run=?"]
            args += [st,json.dumps(sc,ensure_ascii=False),self._iso(nxt)]

        if not sets:
            return self.get(job_id)

        sets.append("updated_at=?");args.append(self._iso());args.append(int(job_id))
        try:
            with self._connect() as conn:
                conn.execute(f"UPDATE automation_jobs SET {','.join(sets)} WHERE id=?",args)
        except sqlite3.IntegrityError as exc:
            return {"ok":False,"error":str(exc)}
        return self.get(job_id)

    def _set_status(self, job_id, status):
        with self._connect() as conn:
            cur=conn.execute(
                "UPDATE automation_jobs SET status=?,updated_at=? WHERE id=?",
                (status,self._iso(),int(job_id))
            )
        return {"ok": cur.rowcount>0, "id": int(job_id), "status": status}

    def enable(self, job_id):
        data=self.get(job_id).get("data")
        if not data:return {"ok":False,"error":"Automação não encontrada."}
        try:nxt=self._compute_next(data["schedule_type"],data["schedule"])
        except Exception as exc:return {"ok":False,"error":str(exc)}
        with self._connect() as conn:
            conn.execute(
                "UPDATE automation_jobs SET status='enabled',next_run=?,updated_at=? WHERE id=?",
                (self._iso(nxt),self._iso(),int(job_id))
            )
        return self.get(job_id)

    def disable(self, job_id): return self._set_status(job_id,"disabled")
    def pause(self, job_id): return self._set_status(job_id,"paused")
    def resume(self, job_id): return self.enable(job_id)

    def delete(self, job_id):
        with self._connect() as conn:
            conn.execute("DELETE FROM automation_runs WHERE job_id=?", (int(job_id),))
            cur=conn.execute("DELETE FROM automation_jobs WHERE id=?", (int(job_id),))
        return {"ok":cur.rowcount>0,"id":int(job_id)}

    def duplicate(self, job_id, new_name):
        data=self.get(job_id).get("data")
        if not data:return {"ok":False,"error":"Automação não encontrada."}
        return self.create(
            new_name,data["schedule_type"],data["target_type"],data["target_id"],
            schedule=data["schedule"],params=data["params"],description=data["description"],
            max_retries=data["max_retries"],retry_backoff_seconds=data["retry_backoff_seconds"],
            tags=data["tags"],require_confirmation=data["require_confirmation"],
            enabled=data["status"]=="enabled",
        )

    def due(self, limit=20):
        now=self._iso()
        with self._connect() as conn:
            rows=conn.execute(
                """SELECT * FROM automation_jobs
                   WHERE status='enabled' AND next_run IS NOT NULL AND next_run<=?
                   ORDER BY next_run ASC LIMIT ?""",
                (now,int(limit))
            ).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def upcoming(self, hours=24, limit=100):
        end=self._now()+timedelta(hours=float(hours))
        with self._connect() as conn:
            rows=conn.execute(
                """SELECT * FROM automation_jobs
                   WHERE status='enabled' AND next_run>? AND next_run<=?
                   ORDER BY next_run ASC LIMIT ?""",
                (self._iso(),self._iso(end),int(limit))
            ).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def overdue(self, minutes=5, limit=100):
        cutoff=self._now()-timedelta(minutes=float(minutes))
        with self._connect() as conn:
            rows=conn.execute(
                """SELECT * FROM automation_jobs
                   WHERE status='enabled' AND next_run IS NOT NULL AND next_run<?
                   ORDER BY next_run ASC LIMIT ?""",
                (self._iso(cutoff),int(limit))
            ).fetchall()
        return {"ok":True,"items":self._rows(rows),"count":len(rows)}

    def _create_run(self, job_id, attempt=1):
        with self._connect() as conn:
            cur=conn.execute(
                "INSERT INTO automation_runs(job_id,started_at,status,attempt) VALUES(?,?,?,?)",
                (int(job_id),self._iso(),"running",int(attempt))
            )
            return int(cur.lastrowid)

    def _finish_run(self, run_id, status, result=None, error=None):
        with self._connect() as conn:
            conn.execute(
                """UPDATE automation_runs SET finished_at=?,status=?,result_json=?,error=?
                   WHERE id=?""",
                (self._iso(),str(status),json.dumps(result or {},ensure_ascii=False,default=str),
                 str(error)[:4000] if error else None,int(run_id))
            )

    def _schedule_after_run(self, job, success, error=None):
        now=self._now()
        if success:
            if job["schedule_type"]=="once":
                status="completed";nxt=None
            else:
                status="enabled";nxt=self._compute_next(job["schedule_type"],job["schedule"],after=now)
            with self._connect() as conn:
                conn.execute(
                    """UPDATE automation_jobs SET status=?,next_run=?,last_run=?,last_status='success',
                       last_error=NULL,run_count=run_count+1,failure_count=0,updated_at=? WHERE id=?""",
                    (status,self._iso(nxt) if nxt else None,self._iso(now),self._iso(now),job["id"])
                )
        else:
            failures=int(job.get("failure_count") or 0)+1
            max_retries=int(job.get("max_retries") or 0)
            if failures<=max_retries:
                backoff=int(job.get("retry_backoff_seconds") or 60)*failures
                nxt=now+timedelta(seconds=backoff)
                status="enabled"
            else:
                nxt=None;status="failed"
            with self._connect() as conn:
                conn.execute(
                    """UPDATE automation_jobs SET status=?,next_run=?,last_run=?,last_status='failed',
                       last_error=?,run_count=run_count+1,failure_count=?,updated_at=? WHERE id=?""",
                    (status,self._iso(nxt) if nxt else None,self._iso(now),str(error)[:4000],
                     failures,self._iso(now),job["id"])
                )

    def execute_job(self, job_id, manual=False):
        if not self._executor:
            return {"ok":False,"error":"Executor de automações não configurado."}

        data=self.get(job_id).get("data")
        if not data:return {"ok":False,"error":"Automação não encontrada."}
        if not manual and data["status"]!="enabled":
            return {"ok":False,"error":f"Automação está {data['status']}."}

        if not manual:
            if self._approval_callback:
                queued=bool(self._approval_callback(data))
                if queued:
                    self._set_status(job_id,"waiting_approval")
                    return {"ok":True,"queued_for_approval":True,"job_id":int(job_id)}
            elif data.get("require_confirmation"):
                return {"ok":False,"error":"Automação requer confirmação e não há approval callback."}

        run_id=self._create_run(job_id,attempt=int(data.get("failure_count") or 0)+1)
        try:
            result=self._executor(data)
            ok=bool(result.get("ok")) if isinstance(result,dict) else True
            if ok:
                self._finish_run(run_id,"success",result=result if isinstance(result,dict) else {"result":str(result)})
                self._schedule_after_run(data,True)
                out={"ok":True,"job_id":int(job_id),"run_id":run_id,"result":result}
                if self._notifier:
                    try:self._notifier(data,out)
                    except Exception:pass
                return out
            err=(result or {}).get("error","Falha na execução.") if isinstance(result,dict) else "Falha."
            self._finish_run(run_id,"failed",result=result if isinstance(result,dict) else {},error=err)
            self._schedule_after_run(data,False,error=err)
            out={"ok":False,"job_id":int(job_id),"run_id":run_id,"error":err}
            if self._notifier:
                try:self._notifier(data,out)
                except Exception:pass
            return out
        except Exception as exc:
            self._finish_run(run_id,"failed",error=str(exc))
            self._schedule_after_run(data,False,error=str(exc))
            out={"ok":False,"job_id":int(job_id),"run_id":run_id,"error":str(exc)}
            if self._notifier:
                try:self._notifier(data,out)
                except Exception:pass
            return out

    def run_now(self, job_id):
        return self.execute_job(job_id,manual=True)

    def reject_approval(self, job_id, reason="Aprovação rejeitada."):
        data=self.get(job_id).get("data")
        if not data:return {"ok":False,"error":"Automação não encontrada."}
        now=self._now()
        if data["schedule_type"]=="once":
            status="cancelled";nxt=None
        else:
            try:nxt=self._compute_next(data["schedule_type"],data["schedule"],after=now)
            except Exception as exc:return {"ok":False,"error":str(exc)}
            status="enabled"
        with self._connect() as conn:
            conn.execute(
                """UPDATE automation_jobs SET status=?,next_run=?,last_status='rejected',
                   last_error=?,updated_at=? WHERE id=?""",
                (status,self._iso(nxt) if nxt else None,str(reason)[:4000],self._iso(now),int(job_id))
            )
        return self.get(job_id)

    def reset_failure(self, job_id):
        data=self.get(job_id).get("data")
        if not data:return {"ok":False,"error":"Automação não encontrada."}
        try:nxt=self._compute_next(data["schedule_type"],data["schedule"])
        except Exception as exc:return {"ok":False,"error":str(exc)}
        with self._connect() as conn:
            conn.execute(
                """UPDATE automation_jobs SET status='enabled',failure_count=0,last_error=NULL,
                   next_run=?,updated_at=? WHERE id=?""",
                (self._iso(nxt),self._iso(),int(job_id))
            )
        return self.get(job_id)

    def history(self, job_id=None, status=None, limit=200):
        sql="""SELECT r.*,j.name job_name,j.target_type,j.target_id
               FROM automation_runs r JOIN automation_jobs j ON j.id=r.job_id WHERE 1=1"""
        args=[]
        if job_id is not None:
            sql+=" AND r.job_id=?";args.append(int(job_id))
        if status:
            sql+=" AND r.status=?";args.append(str(status))
        sql+=" ORDER BY r.id DESC LIMIT ?";args.append(int(limit))
        with self._connect() as conn:
            rows=conn.execute(sql,args).fetchall()
        out=[]
        for r in rows:
            d=dict(r)
            try:d["result"]=json.loads(d.pop("result_json") or "{}")
            except Exception:d["result"]={}
            out.append(d)
        return {"ok":True,"items":out,"count":len(out)}

    def clear_history(self, older_than_days=30):
        cutoff=self._now()-timedelta(days=float(older_than_days))
        with self._connect() as conn:
            cur=conn.execute("DELETE FROM automation_runs WHERE started_at<?",(self._iso(cutoff),))
        return {"ok":True,"removed":cur.rowcount}

    def stats(self):
        with self._connect() as conn:
            total=conn.execute("SELECT COUNT(*) n FROM automation_jobs").fetchone()["n"]
            rows=conn.execute("SELECT status,COUNT(*) n FROM automation_jobs GROUP BY status").fetchall()
            runs=conn.execute("SELECT COUNT(*) n FROM automation_runs").fetchone()["n"]
            failed=conn.execute("SELECT COUNT(*) n FROM automation_runs WHERE status='failed'").fetchone()["n"]
        return {
            "ok":True,"jobs":total,"runs":runs,"failed_runs":failed,
            "statuses":{r["status"]:r["n"] for r in rows}
        }

    def export_jobs(self, path):
        out=Path(path).expanduser().resolve()
        out.parent.mkdir(parents=True,exist_ok=True)
        data=self.list(limit=10000)["items"]
        out.write_text(json.dumps(data,indent=2,ensure_ascii=False,default=str),encoding="utf-8")
        return {"ok":True,"path":str(out),"jobs":len(data)}

    def import_jobs(self, path, overwrite=False):
        p=Path(path).expanduser().resolve()
        if not p.is_file():return {"ok":False,"error":"Arquivo não encontrado."}
        try:data=json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:return {"ok":False,"error":str(exc)}
        if not isinstance(data,list):return {"ok":False,"error":"JSON deve ser uma lista."}
        created=[];errors=[]
        for item in data:
            name=item.get("name")
            if overwrite:
                existing=self.get(name=name).get("data")
                if existing:self.delete(existing["id"])
            r=self.create(
                name=name,schedule_type=item.get("schedule_type","once"),
                target_type=item.get("target_type","action"),target_id=item.get("target_id",""),
                schedule=item.get("schedule",{}),params=item.get("params",{}),
                description=item.get("description",""),max_retries=item.get("max_retries",2),
                retry_backoff_seconds=item.get("retry_backoff_seconds",60),tags=item.get("tags",[]),
                require_confirmation=item.get("require_confirmation",False),
                enabled=item.get("status","enabled")=="enabled"
            )
            (created if r.get("ok") else errors).append(r)
        return {"ok":not errors,"created":len(created),"errors":errors}

    def tick(self, limit=10):
        items=self.due(limit=limit)["items"]
        results=[]
        for item in items:
            results.append(self.execute_job(item["id"],manual=False))
        return {"ok":True,"checked":len(items),"results":results}

    def start_worker(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return {"ok":True,"running":True}
            self._stop.clear()
            self._thread=threading.Thread(target=self._loop,name="JarvisAutomationWorker",daemon=True)
            self._thread.start()
        return {"ok":True,"running":True}

    def stop_worker(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        return {"ok":True,"running":False}

    def worker_status(self):
        return {"ok":True,"running":bool(self._thread and self._thread.is_alive()),"poll_seconds":self.poll_seconds}

    def _loop(self):
        while not self._stop.wait(self.poll_seconds):
            try:
                self.tick(limit=10)
            except Exception:
                pass

    def execute(self, operation, **params):
        mapping={
            "create":self.create,"list":self.list,"get":self.get,"update":self.update,
            "delete":self.delete,"enable":self.enable,"disable":self.disable,
            "pause":self.pause,"resume":self.resume,"duplicate":self.duplicate,
            "due":self.due,"upcoming":self.upcoming,"overdue":self.overdue,
            "run_now":self.run_now,"reject_approval":self.reject_approval,"reset_failure":self.reset_failure,
            "history":self.history,"clear_history":self.clear_history,
            "stats":self.stats,"export":self.export_jobs,"import":self.import_jobs,
            "tick":self.tick,"worker_start":self.start_worker,"worker_stop":self.stop_worker,
            "worker_status":self.worker_status,
        }
        fn=mapping.get(operation)
        if not fn:return {"ok":False,"error":f"Operação de automação desconhecida: {operation}"}
        return fn(**params)
