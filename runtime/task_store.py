import json
import sqlite3
from datetime import datetime
from pathlib import Path


class TaskStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    final_result TEXT,
                    plan_json TEXT,
                    current_step INTEGER DEFAULT 0,
                    heartbeat_at TEXT,
                    attempts INTEGER DEFAULT 0,
                    last_error TEXT
                );
                CREATE TABLE IF NOT EXISTS task_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    step INTEGER NOT NULL,
                    tool TEXT,
                    args_json TEXT,
                    ok INTEGER,
                    result_text TEXT,
                    created_at TEXT NOT NULL
                );
            """)
            # Migra bancos criados por releases anteriores sem perder histórico.
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(tasks)").fetchall()}
            if "plan_json" not in columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN plan_json TEXT")
            if "current_step" not in columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN current_step INTEGER DEFAULT 0")
            if "heartbeat_at" not in columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN heartbeat_at TEXT")
            if "attempts" not in columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN attempts INTEGER DEFAULT 0")
            if "last_error" not in columns:
                conn.execute("ALTER TABLE tasks ADD COLUMN last_error TEXT")

    def start(self, goal):
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO tasks(goal,status,started_at,heartbeat_at,attempts) VALUES(?,?,?,?,?)",
                (str(goal), "running", now, now, 1),
            )
            return int(cur.lastrowid)

    def heartbeat(self, task_id, status=None):
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            if status:
                conn.execute("UPDATE tasks SET heartbeat_at=?, status=? WHERE id=?", (now, str(status), int(task_id)))
            else:
                conn.execute("UPDATE tasks SET heartbeat_at=? WHERE id=?", (now, int(task_id)))
        return {"ok": True, "task_id": int(task_id), "heartbeat_at": now}

    def set_status(self, task_id, status, error=None):
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                "UPDATE tasks SET status=?, heartbeat_at=?, last_error=? WHERE id=?",
                (str(status), now, str(error)[:4000] if error else None, int(task_id)),
            )
        return {"ok": True, "task_id": int(task_id), "status": str(status)}

    def retry(self, task_id, error=None):
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                "UPDATE tasks SET status='retrying', heartbeat_at=?, attempts=COALESCE(attempts,0)+1, last_error=? WHERE id=?",
                (now, str(error)[:4000] if error else None, int(task_id)),
            )
        return {"ok": True, "task_id": int(task_id), "status": "retrying"}

    def event(self, task_id, step, tool, args, result):
        now = datetime.now().isoformat(timespec="seconds")
        ok = 1 if result.get("ok") else 0
        compact = json.dumps(result, ensure_ascii=False, default=str)
        if len(compact) > 12000:
            compact = compact[:12000] + "..."
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO task_events(task_id,step,tool,args_json,ok,result_text,created_at) VALUES(?,?,?,?,?,?,?)",
                (task_id, int(step), str(tool), json.dumps(args, ensure_ascii=False), ok, compact, now),
            )
            conn.execute("UPDATE tasks SET heartbeat_at=? WHERE id=?", (now, int(task_id)))


    def set_plan(self, task_id, steps):
        clean = [str(x).strip() for x in (steps or []) if str(x).strip()]
        with self._connect() as conn:
            conn.execute(
                "UPDATE tasks SET plan_json=?, current_step=0 WHERE id=?",
                (json.dumps(clean, ensure_ascii=False), int(task_id)),
            )
        return {"ok": True, "task_id": int(task_id), "steps": clean}

    def advance_plan(self, task_id, step=None):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT current_step,plan_json FROM tasks WHERE id=?",
                (int(task_id),)
            ).fetchone()
            if not row:
                return {"ok": False, "error": "Tarefa não encontrada."}
            current = int(row["current_step"] or 0)
            new_value = int(step) if step is not None else current + 1
            conn.execute(
                "UPDATE tasks SET current_step=? WHERE id=?",
                (new_value, int(task_id))
            )
            try:
                plan = json.loads(row["plan_json"] or "[]")
            except Exception:
                plan = []
        return {"ok": True, "task_id": int(task_id), "current_step": new_value, "plan": plan}

    def get(self, task_id):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id=?", (int(task_id),)).fetchone()
        if not row:
            return None
        item = dict(row)
        try:
            item["plan"] = json.loads(item.get("plan_json") or "[]")
        except Exception:
            item["plan"] = []
        return item

    def finish(self, task_id, result, status="completed"):
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                "UPDATE tasks SET status=?, finished_at=?, heartbeat_at=?, final_result=?, last_error=? WHERE id=?",
                (status, now, now, str(result)[:12000], str(result)[:4000] if status in {"failed","interrupted"} else None, int(task_id)),
            )

    def recent(self, limit=15):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (int(limit),)
            ).fetchall()
        items = []
        for r in rows:
            item = dict(r)
            try:
                item["plan"] = json.loads(item.get("plan_json") or "[]")
            except Exception:
                item["plan"] = []
            items.append(item)
        return items

    def active(self):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE status IN ('running','planning','retrying','waiting_user') ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        try:
            item["plan"] = json.loads(item.get("plan_json") or "[]")
        except Exception:
            item["plan"] = []
        return item

    def stale_tasks(self, stale_after_seconds=300):
        now = datetime.now()
        statuses = ("running","planning","retrying","waiting_user")
        placeholders = ",".join("?" for _ in statuses)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM tasks WHERE status IN ({placeholders}) ORDER BY id DESC", statuses
            ).fetchall()
        items=[]
        for row in rows:
            item=dict(row)
            stamp=item.get("heartbeat_at") or item.get("started_at")
            try:
                dt=datetime.fromisoformat(stamp); age=(now-dt).total_seconds()
            except Exception:
                age=999999
            item["age_seconds"]=round(age,1)
            if age>=float(stale_after_seconds): items.append(item)
        return {"items":items,"count":len(items)}

    def reconcile_stale(self, stale_after_seconds=10, reason="Sessão anterior interrompida."):
        stale=self.stale_tasks(stale_after_seconds=stale_after_seconds)
        now=datetime.now().isoformat(timespec="seconds")
        ids=[int(x["id"]) for x in stale.get("items",[])]
        if ids:
            with self._connect() as conn:
                for task_id in ids:
                    conn.execute(
                        "UPDATE tasks SET status='interrupted', finished_at=?, heartbeat_at=?, last_error=?, final_result=? WHERE id=?",
                        (now,now,str(reason)[:4000],str(reason)[:12000],task_id),
                    )
        return {"ok":True,"interrupted":len(ids),"task_ids":ids}

    def events(self, task_id, limit=200):
        with self._connect() as conn:
            rows=conn.execute(
                "SELECT * FROM task_events WHERE task_id=? ORDER BY id ASC LIMIT ?",
                (int(task_id),int(limit))
            ).fetchall()
        return {"ok":True,"items":[dict(r) for r in rows],"count":len(rows)}
