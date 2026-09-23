import json
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path


WRITE_RISK_MARKERS = (
    "publicar", "publique", "postar", "poste", "enviar", "envie", "deletar", "excluir",
    "apagar", "mover", "renomear", "alterar", "editar", "salvar no sistema", "cadastrar",
    "criar usuário", "criar usuario", "aprovar", "rejeitar", "comprar", "pagar",
)


class LongHorizonEngine:
    """
    Jobs persistentes de longo prazo.

    Princípios:
    - cada etapa é checkpointada;
    - reinício do Jarvis não apaga o job;
    - passos de leitura/pesquisa podem ser retomados automaticamente;
    - passos potencialmente destrutivos interrompidos durante execução não são
      repetidos silenciosamente;
    - o worker executa um passo por vez e persiste tudo entre os passos.
    """

    ACTIVE = {"queued", "planning", "running", "retrying", "waiting_user", "paused", "pausing"}
    TERMINAL = {"completed", "failed", "cancelled"}

    def __init__(self, db_path, config=None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.config = dict(config or {})
        self.poll_seconds = max(1, int(self.config.get("long_horizon_poll_seconds", 3)))
        self.max_retries = max(0, int(self.config.get("long_horizon_max_retries", 3)))
        self.max_steps = max(2, int(self.config.get("long_horizon_max_steps", 8)))
        self.retry_base = max(2, int(self.config.get("long_horizon_retry_base_seconds", 8)))

        self._planner = None
        self._executor = None
        self._notifier = None
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self):
        c = sqlite3.connect(self.db_path, timeout=20)
        c.row_factory = sqlite3.Row
        return c

    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def _init_db(self):
        with self._connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS long_jobs(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              goal TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'queued',
              priority INTEGER NOT NULL DEFAULT 50,
              auto_resume INTEGER NOT NULL DEFAULT 1,
              project_id INTEGER,
              session_id INTEGER,
              current_step INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              started_at TEXT,
              finished_at TEXT,
              next_run_at TEXT,
              attempts INTEGER NOT NULL DEFAULT 0,
              max_retries INTEGER NOT NULL DEFAULT 3,
              final_result TEXT,
              last_error TEXT,
              metadata_json TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS long_job_steps(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_id INTEGER NOT NULL,
              position INTEGER NOT NULL,
              title TEXT NOT NULL,
              instruction TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending',
              retry_safe INTEGER NOT NULL DEFAULT 1,
              attempts INTEGER NOT NULL DEFAULT 0,
              started_at TEXT,
              completed_at TEXT,
              result_text TEXT,
              last_error TEXT,
              UNIQUE(job_id, position)
            );

            CREATE TABLE IF NOT EXISTS long_job_checkpoints(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_id INTEGER NOT NULL,
              step_position INTEGER NOT NULL,
              state_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS long_job_events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_id INTEGER NOT NULL,
              event_type TEXT NOT NULL,
              message TEXT NOT NULL,
              payload_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_long_jobs_status ON long_jobs(status,next_run_at,priority,id);
            CREATE INDEX IF NOT EXISTS idx_long_steps_job ON long_job_steps(job_id,position);
            CREATE INDEX IF NOT EXISTS idx_long_events_job ON long_job_events(job_id,id);
            """)

    def set_planner(self, fn):
        self._planner = fn

    def set_executor(self, fn):
        self._executor = fn

    def set_notifier(self, fn):
        self._notifier = fn

    def _event(self, job_id, kind, message, payload=None):
        with self._connect() as c:
            c.execute(
                "INSERT INTO long_job_events(job_id,event_type,message,payload_json,created_at) VALUES(?,?,?,?,?)",
                (int(job_id), str(kind), str(message)[:4000],
                 json.dumps(payload or {}, ensure_ascii=False, default=str), self._now())
            )

    def _notify(self, job, result):
        if not self._notifier:
            return
        try:
            self._notifier(job, result)
        except Exception:
            pass

    def _normalize_step(self, raw, position):
        if isinstance(raw, str):
            title = raw.strip() or f"Etapa {position+1}"
            instruction = title
            retry_safe = not any(x in title.lower() for x in WRITE_RISK_MARKERS)
        else:
            raw = dict(raw or {})
            title = str(raw.get("title") or raw.get("name") or f"Etapa {position+1}").strip()
            instruction = str(raw.get("instruction") or raw.get("prompt") or title).strip()
            if "retry_safe" in raw:
                retry_safe = bool(raw.get("retry_safe"))
            else:
                low = (title + " " + instruction).lower()
                retry_safe = not any(x in low for x in WRITE_RISK_MARKERS)
        return {
            "position": int(position),
            "title": title[:300],
            "instruction": instruction[:6000],
            "retry_safe": 1 if retry_safe else 0,
        }

    def create(self, goal, plan=None, project_id=None, session_id=None,
               auto_resume=True, priority=50, metadata=None):
        goal = str(goal or "").strip()
        if not goal:
            return {"ok": False, "error": "Objetivo do job é obrigatório."}
        now = self._now()
        with self._connect() as c:
            cur = c.execute(
                """INSERT INTO long_jobs(
                    goal,status,priority,auto_resume,project_id,session_id,current_step,
                    created_at,updated_at,max_retries,metadata_json
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (goal, "queued", int(priority), 1 if auto_resume else 0,
                 int(project_id) if project_id else None,
                 int(session_id) if session_id else None,
                 0, now, now, self.max_retries,
                 json.dumps(metadata or {}, ensure_ascii=False, default=str))
            )
            job_id = int(cur.lastrowid)

        if plan:
            self.set_plan(job_id, plan)
        self._event(job_id, "created", "Job persistente criado.", {"goal": goal})
        return self.get(job_id)

    def set_plan(self, job_id, plan):
        clean = [self._normalize_step(x, i) for i, x in enumerate(plan or [])][:self.max_steps]
        if not clean:
            return {"ok": False, "error": "Plano vazio."}
        with self._connect() as c:
            c.execute("DELETE FROM long_job_steps WHERE job_id=?", (int(job_id),))
            for step in clean:
                c.execute(
                    """INSERT INTO long_job_steps(
                        job_id,position,title,instruction,status,retry_safe
                       ) VALUES(?,?,?,?,?,?)""",
                    (int(job_id), step["position"], step["title"], step["instruction"],
                     "pending", step["retry_safe"])
                )
            c.execute(
                "UPDATE long_jobs SET current_step=0,status='queued',updated_at=? WHERE id=?",
                (self._now(), int(job_id))
            )
        self._event(job_id, "planned", f"Plano definido com {len(clean)} etapas.",
                    {"steps": [x["title"] for x in clean]})
        return {"ok": True, "job_id": int(job_id), "steps": clean}

    def _row_job(self, row):
        if not row:
            return None
        d = dict(row)
        try:
            d["metadata"] = json.loads(d.pop("metadata_json") or "{}")
        except Exception:
            d["metadata"] = {}
        d["auto_resume"] = bool(d.get("auto_resume"))
        return d

    def steps(self, job_id):
        with self._connect() as c:
            rows = c.execute(
                "SELECT * FROM long_job_steps WHERE job_id=? ORDER BY position ASC",
                (int(job_id),)
            ).fetchall()
        items = [dict(x) for x in rows]
        for x in items:
            x["retry_safe"] = bool(x.get("retry_safe"))
        return items

    def get(self, job_id):
        with self._connect() as c:
            row = c.execute("SELECT * FROM long_jobs WHERE id=?", (int(job_id),)).fetchone()
        if not row:
            return {"ok": False, "error": "Job não encontrado."}
        job = self._row_job(row)
        job["steps"] = self.steps(job_id)
        job["progress"] = self.progress(job_id)
        return {"ok": True, "data": job}

    def list(self, status=None, limit=50):
        sql = "SELECT * FROM long_jobs"
        args = []
        if status:
            sql += " WHERE status=?"
            args.append(str(status))
        sql += " ORDER BY CASE WHEN status IN ('running','planning','queued','retrying','waiting_user') THEN 0 ELSE 1 END, priority DESC, id DESC LIMIT ?"
        args.append(int(limit))
        with self._connect() as c:
            rows = c.execute(sql, args).fetchall()
        items = []
        for row in rows:
            item = self._row_job(row)
            item["progress"] = self.progress(item["id"])
            items.append(item)
        return {"ok": True, "items": items, "count": len(items)}

    def progress(self, job_id):
        with self._connect() as c:
            rows = c.execute(
                "SELECT status,COUNT(*) n FROM long_job_steps WHERE job_id=? GROUP BY status",
                (int(job_id),)
            ).fetchall()
        counts = {x["status"]: int(x["n"]) for x in rows}
        total = sum(counts.values())
        completed = counts.get("completed", 0)
        percent = round((completed / total) * 100) if total else 0
        return {"total": total, "completed": completed, "percent": percent, "statuses": counts}

    def events(self, job_id, limit=200):
        with self._connect() as c:
            rows = c.execute(
                "SELECT * FROM long_job_events WHERE job_id=? ORDER BY id ASC LIMIT ?",
                (int(job_id), int(limit))
            ).fetchall()
        items = []
        for row in rows:
            d = dict(row)
            try:
                d["payload"] = json.loads(d.pop("payload_json") or "{}")
            except Exception:
                d["payload"] = {}
            items.append(d)
        return {"ok": True, "items": items, "count": len(items)}

    def checkpoints(self, job_id, limit=50):
        with self._connect() as c:
            rows = c.execute(
                "SELECT * FROM long_job_checkpoints WHERE job_id=? ORDER BY id DESC LIMIT ?",
                (int(job_id), int(limit))
            ).fetchall()
        items = []
        for row in rows:
            d = dict(row)
            try:
                d["state"] = json.loads(d.pop("state_json") or "{}")
            except Exception:
                d["state"] = {}
            items.append(d)
        return {"ok": True, "items": items, "count": len(items)}

    def _checkpoint(self, job_id, position, state):
        with self._connect() as c:
            c.execute(
                "INSERT INTO long_job_checkpoints(job_id,step_position,state_json,created_at) VALUES(?,?,?,?)",
                (int(job_id), int(position), json.dumps(state or {}, ensure_ascii=False, default=str), self._now())
            )

    def pause(self, job_id):
        got = self.get(job_id)
        if not got.get("ok"):
            return got
        current = got["data"]
        target = "pausing" if current.get("status") == "running" else "paused"
        with self._connect() as c:
            cur = c.execute(
                "UPDATE long_jobs SET status=?,updated_at=? WHERE id=? AND status NOT IN ('completed','cancelled')",
                (target, self._now(), int(job_id))
            )
        self._event(
            job_id, "pause_requested" if target == "pausing" else "paused",
            "Pausa solicitada; o job parará no próximo checkpoint." if target == "pausing" else "Job pausado."
        )
        return {"ok": cur.rowcount > 0, "job_id": int(job_id), "status": target}

    def resume(self, job_id, force=False):
        got = self.get(job_id)
        if not got.get("ok"):
            return got
        job = got["data"]
        if job["status"] in self.TERMINAL and job["status"] != "failed":
            return {"ok": False, "error": f"Job está {job['status']}."}

        current = next((x for x in job.get("steps", []) if int(x["position"]) == int(job.get("current_step", 0))), None)
        if current and current.get("status") == "running":
            if not current.get("retry_safe") and not force:
                return {
                    "ok": False,
                    "error": "A última etapa pode ter causado efeito externo antes da interrupção. Use retomada forçada somente após verificar o estado real."
                }
            with self._connect() as c:
                c.execute(
                    "UPDATE long_job_steps SET status='pending',started_at=NULL WHERE id=?",
                    (int(current["id"]),)
                )

        with self._connect() as c:
            c.execute(
                "UPDATE long_jobs SET status='queued',next_run_at=NULL,last_error=NULL,updated_at=? WHERE id=?",
                (self._now(), int(job_id))
            )
        self._event(job_id, "resumed", "Job colocado novamente na fila.", {"force": bool(force)})
        return {"ok": True, "job_id": int(job_id), "status": "queued"}

    def cancel(self, job_id):
        now = self._now()
        with self._connect() as c:
            cur = c.execute(
                "UPDATE long_jobs SET status='cancelled',finished_at=?,updated_at=? WHERE id=? AND status NOT IN ('completed','cancelled')",
                (now, now, int(job_id))
            )
        self._event(job_id, "cancelled", "Job cancelado pelo usuário.")
        return {"ok": cur.rowcount > 0, "job_id": int(job_id), "status": "cancelled"}

    def stats(self):
        with self._connect() as c:
            rows = c.execute("SELECT status,COUNT(*) n FROM long_jobs GROUP BY status").fetchall()
            total = c.execute("SELECT COUNT(*) n FROM long_jobs").fetchone()["n"]
        statuses = {x["status"]: int(x["n"]) for x in rows}
        active = sum(statuses.get(x, 0) for x in ("queued","planning","running","retrying","waiting_user","pausing"))
        return {"ok": True, "jobs": int(total), "active": int(active), "statuses": statuses}

    def _needs_user(self, text):
        low = str(text or "").lower()
        markers = (
            "aprovação necessária", "aprovacao necessaria", "aguarda autorização",
            "aguarda autorizacao", "requer confirmação", "requer confirmacao",
            "preciso que você", "preciso que voce", "faça login", "faca login",
            "autentique", "confirme manualmente",
        )
        return any(x in low for x in markers)

    def _ensure_plan(self, job):
        if self.steps(job["id"]):
            return {"ok": True}
        with self._connect() as c:
            c.execute(
                "UPDATE long_jobs SET status='planning',updated_at=? WHERE id=?",
                (self._now(), int(job["id"]))
            )
        self._event(job["id"], "planning", "Planejando job de longo prazo.")

        plan = None
        if self._planner:
            try:
                result = self._planner(job)
                if isinstance(result, dict):
                    plan = result.get("steps") or result.get("plan")
                elif isinstance(result, list):
                    plan = result
            except Exception as exc:
                self._event(job["id"], "planner_error", str(exc))

        if not plan:
            plan = [
                {
                    "title": "Analisar objetivo e contexto",
                    "instruction": f"Analise o objetivo '{job['goal']}' e reúna o contexto necessário para executá-lo com segurança.",
                    "retry_safe": True,
                },
                {
                    "title": "Executar o objetivo",
                    "instruction": f"Execute a parte principal do objetivo: {job['goal']}. Use as ferramentas disponíveis e registre limitações concretas.",
                    "retry_safe": not any(x in job["goal"].lower() for x in WRITE_RISK_MARKERS),
                },
                {
                    "title": "Verificar resultado",
                    "instruction": f"Verifique de forma independente se o objetivo foi cumprido: {job['goal']}. Corrija inconsistências seguras e registre o resultado final.",
                    "retry_safe": True,
                },
            ]
        return self.set_plan(job["id"], plan)

    def recover_on_start(self):
        recovered = []
        waiting = []
        with self._connect() as c:
            rows = c.execute(
                "SELECT * FROM long_jobs WHERE status IN ('planning','running','retrying')"
            ).fetchall()

        for row in rows:
            job = self._row_job(row)
            steps = self.steps(job["id"])
            current = next((x for x in steps if int(x["position"]) == int(job.get("current_step", 0))), None)

            if current and current.get("status") == "running":
                if bool(current.get("retry_safe")) and job.get("auto_resume"):
                    with self._connect() as c:
                        c.execute(
                            "UPDATE long_job_steps SET status='pending',started_at=NULL,last_error=? WHERE id=?",
                            ("Etapa interrompida pelo encerramento anterior; retomada automática segura.", int(current["id"]))
                        )
                        c.execute(
                            "UPDATE long_jobs SET status='queued',next_run_at=NULL,updated_at=?,last_error=? WHERE id=?",
                            (self._now(), "Retomando após reinício.", int(job["id"]))
                        )
                    recovered.append(job["id"])
                    self._event(job["id"], "recovered", "Etapa segura recolocada na fila após reinício.")
                else:
                    with self._connect() as c:
                        c.execute(
                            "UPDATE long_jobs SET status='waiting_user',updated_at=?,last_error=? WHERE id=?",
                            (self._now(),
                             "O Jarvis foi encerrado durante uma etapa com possível efeito externo. Verifique o estado antes de retomar.",
                             int(job["id"]))
                        )
                    waiting.append(job["id"])
                    self._event(job["id"], "recovery_review", "Retomada automática bloqueada por segurança.")
            elif job.get("auto_resume"):
                with self._connect() as c:
                    c.execute(
                        "UPDATE long_jobs SET status='queued',next_run_at=NULL,updated_at=? WHERE id=?",
                        (self._now(), int(job["id"]))
                    )
                recovered.append(job["id"])
                self._event(job["id"], "recovered", "Job recolocado na fila após reinício.")
            else:
                with self._connect() as c:
                    c.execute(
                        "UPDATE long_jobs SET status='paused',updated_at=? WHERE id=?",
                        (self._now(), int(job["id"]))
                    )
        return {"ok": True, "recovered": recovered, "waiting_review": waiting}

    def _due_job(self):
        now = self._now()
        with self._connect() as c:
            row = c.execute(
                """SELECT * FROM long_jobs
                   WHERE status IN ('queued','retrying')
                     AND (next_run_at IS NULL OR next_run_at<=?)
                   ORDER BY priority DESC,id ASC LIMIT 1""",
                (now,)
            ).fetchone()
        return self._row_job(row)

    def _run_one(self, job):
        ensured = self._ensure_plan(job)
        if not ensured.get("ok"):
            raise RuntimeError(ensured.get("error", "Falha no planejamento."))

        got = self.get(job["id"])
        job = got["data"]
        steps = job["steps"]

        # Skip already completed steps and synchronize pointer.
        pending = [x for x in steps if x.get("status") != "completed"]
        if not pending:
            result = "\n".join(
                str(x.get("result_text") or "") for x in steps if x.get("result_text")
            )[-12000:]
            now = self._now()
            with self._connect() as c:
                c.execute(
                    "UPDATE long_jobs SET status='completed',finished_at=?,updated_at=?,final_result=? WHERE id=?",
                    (now, now, result, int(job["id"]))
                )
            self._event(job["id"], "completed", "Job concluído.")
            final_job = self.get(job["id"])["data"]
            self._notify(final_job, {"ok": True, "status": "completed"})
            return

        step = pending[0]
        position = int(step["position"])

        with self._connect() as c:
            c.execute(
                "UPDATE long_jobs SET status='running',current_step=?,started_at=COALESCE(started_at,?),updated_at=? WHERE id=?",
                (position, self._now(), self._now(), int(job["id"]))
            )
            c.execute(
                "UPDATE long_job_steps SET status='running',attempts=attempts+1,started_at=?,last_error=NULL WHERE id=?",
                (self._now(), int(step["id"]))
            )
        self._checkpoint(job["id"], position, {
            "phase": "before_step",
            "title": step["title"],
            "retry_safe": bool(step["retry_safe"]),
        })
        self._event(job["id"], "step_start", f"Etapa {position+1}: {step['title']}")

        if not self._executor:
            raise RuntimeError("Executor de Long-Horizon não configurado.")

        result = self._executor(self.get(job["id"])["data"], dict(step))
        if isinstance(result, str):
            result = {"ok": True, "output": result}
        result = dict(result or {})
        output = str(result.get("output") or result.get("message") or result.get("result") or "")
        ok = bool(result.get("ok", False))
        error = str(result.get("error") or ("" if ok else output) or "Falha sem detalhe.")

        # Pause/cancel are checkpoint-safe: the current model/tool call is not
        # killed mid-operation, but its result cannot reactivate the job.
        latest = self.get(job["id"])
        latest_status = (latest.get("data") or {}).get("status") if latest.get("ok") else None
        if latest_status == "cancelled":
            if ok:
                with self._connect() as c:
                    c.execute(
                        "UPDATE long_job_steps SET status='completed',completed_at=?,result_text=? WHERE id=?",
                        (self._now(), output[:20000], int(step["id"]))
                    )
            self._checkpoint(job["id"], position, {
                "phase": "cancelled_after_step",
                "ok": ok,
                "output": output[:8000],
                "error": error[:4000],
            })
            self._event(job["id"], "cancel_checkpoint", "Etapa corrente terminou após o cancelamento; job permanece cancelado.")
            return

        if latest_status in {"pausing", "paused"}:
            with self._connect() as c:
                c.execute(
                    """UPDATE long_job_steps
                       SET status=?,completed_at=?,result_text=?,last_error=?
                       WHERE id=?""",
                    (
                        "completed" if ok else "pending",
                        self._now() if ok else None,
                        output[:20000] if ok else None,
                        None if ok else error[:4000],
                        int(step["id"])
                    )
                )
                c.execute(
                    "UPDATE long_jobs SET status='paused',current_step=?,updated_at=?,last_error=? WHERE id=?",
                    (position + 1 if ok else position, self._now(), None if ok else error[:4000], int(job["id"]))
                )
            self._checkpoint(job["id"], position, {
                "phase": "paused_after_step",
                "ok": ok,
                "output": output[:8000],
                "error": error[:4000],
            })
            self._event(job["id"], "paused", "Job pausado no checkpoint após concluir a etapa corrente.")
            return

        if ok and not self._needs_user(output):
            now = self._now()
            with self._connect() as c:
                c.execute(
                    """UPDATE long_job_steps
                       SET status='completed',completed_at=?,result_text=?,last_error=NULL
                       WHERE id=?""",
                    (now, output[:20000], int(step["id"]))
                )
                c.execute(
                    "UPDATE long_jobs SET status='queued',current_step=?,updated_at=?,next_run_at=NULL,last_error=NULL WHERE id=?",
                    (position + 1, now, int(job["id"]))
                )
            self._checkpoint(job["id"], position, {
                "phase": "after_step",
                "ok": True,
                "output": output[:8000],
            })
            self._event(job["id"], "step_complete", f"Etapa {position+1} concluída.", {"output": output[:1200]})
            # One step per worker cycle = natural checkpoint boundary.
            return

        if self._needs_user(output + " " + error):
            with self._connect() as c:
                c.execute(
                    "UPDATE long_job_steps SET status='waiting_user',last_error=? WHERE id=?",
                    ((error or output)[:4000], int(step["id"]))
                )
                c.execute(
                    "UPDATE long_jobs SET status='waiting_user',updated_at=?,last_error=? WHERE id=?",
                    (self._now(), (error or output)[:4000], int(job["id"]))
                )
            self._event(job["id"], "waiting_user", "Job aguarda intervenção/autorização do usuário.",
                        {"detail": (error or output)[:1200]})
            self._notify(self.get(job["id"])["data"], {"ok": False, "status": "waiting_user", "error": error or output})
            return

        attempts = int(step.get("attempts") or 0) + 1
        if attempts <= int(job.get("max_retries") or self.max_retries):
            delay = min(300, self.retry_base * (2 ** max(0, attempts - 1)))
            next_run = (datetime.now() + timedelta(seconds=delay)).isoformat(timespec="seconds")
            with self._connect() as c:
                c.execute(
                    "UPDATE long_job_steps SET status='pending',last_error=? WHERE id=?",
                    (error[:4000], int(step["id"]))
                )
                c.execute(
                    "UPDATE long_jobs SET status='retrying',attempts=attempts+1,next_run_at=?,updated_at=?,last_error=? WHERE id=?",
                    (next_run, self._now(), error[:4000], int(job["id"]))
                )
            self._event(job["id"], "retry", f"Etapa falhou; nova tentativa em {delay}s.",
                        {"error": error[:1200], "delay": delay})
            return

        now = self._now()
        with self._connect() as c:
            c.execute(
                "UPDATE long_job_steps SET status='failed',completed_at=?,last_error=? WHERE id=?",
                (now, error[:4000], int(step["id"]))
            )
            c.execute(
                "UPDATE long_jobs SET status='failed',finished_at=?,updated_at=?,last_error=? WHERE id=?",
                (now, now, error[:4000], int(job["id"]))
            )
        self._event(job["id"], "failed", "Job falhou após esgotar tentativas.", {"error": error[:1200]})
        self._notify(self.get(job["id"])["data"], {"ok": False, "status": "failed", "error": error})

    def run_now(self, job_id):
        got = self.get(job_id)
        if not got.get("ok"):
            return got
        job = got["data"]
        if job["status"] in {"paused", "waiting_user", "failed"}:
            resumed = self.resume(job_id, force=False)
            if not resumed.get("ok"):
                return resumed
            job = self.get(job_id)["data"]
        try:
            self._run_one(job)
            return self.get(job_id)
        except Exception as exc:
            self._event(job_id, "worker_error", str(exc))
            return {"ok": False, "error": str(exc), "job_id": int(job_id)}

    def _loop(self):
        while not self._stop.wait(self.poll_seconds):
            try:
                job = self._due_job()
                if not job:
                    continue
                self._run_one(job)
            except Exception as exc:
                try:
                    if job:
                        with self._connect() as c:
                            c.execute(
                                "UPDATE long_jobs SET status='retrying',updated_at=?,last_error=? WHERE id=?",
                                (self._now(), str(exc)[:4000], int(job["id"]))
                            )
                        self._event(job["id"], "worker_error", str(exc))
                except Exception:
                    pass

    def start_worker(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return {"ok": True, "running": True}
            recovery = self.recover_on_start()
            self._stop.clear()
            self._thread = threading.Thread(target=self._loop, daemon=True, name="JarvisLongHorizon")
            self._thread.start()
            return {"ok": True, "running": True, "recovery": recovery}

    def stop_worker(self):
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=max(1, self.poll_seconds + 1))
        return {"ok": True, "running": False}

    def worker_status(self):
        return {
            "ok": True,
            "running": bool(self._thread and self._thread.is_alive()),
            "poll_seconds": self.poll_seconds,
        }
