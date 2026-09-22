import json
import sqlite3
from datetime import datetime
from pathlib import Path


class ImprovementQueue:
    """Fila supervisionada para evolução do próprio Jarvis."""

    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        c = sqlite3.connect(self.db_path, timeout=20)
        c.row_factory = sqlite3.Row
        return c

    def _now(self):
        return datetime.now().isoformat(timespec="seconds")

    def _init_db(self):
        with self._connect() as c:
            c.execute("""
            CREATE TABLE IF NOT EXISTS improvement_proposals(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TEXT NOT NULL,
              kind TEXT NOT NULL,
              title TEXT NOT NULL,
              description TEXT NOT NULL,
              evidence_json TEXT NOT NULL DEFAULT '{}',
              status TEXT NOT NULL DEFAULT 'proposed',
              priority INTEGER NOT NULL DEFAULT 50,
              resolution_note TEXT DEFAULT ''
            )""")

    def propose(self, kind, title, description, evidence=None, priority=50):
        with self._connect() as c:
            row = c.execute(
                "SELECT id FROM improvement_proposals WHERE status='proposed' AND lower(title)=lower(?)",
                (str(title),)
            ).fetchone()
            if row:
                return self.get(int(row["id"]))
            cur = c.execute(
                """INSERT INTO improvement_proposals(created_at,kind,title,description,evidence_json,status,priority)
                   VALUES(?,?,?,?,?,'proposed',?)""",
                (self._now(), str(kind), str(title), str(description),
                 json.dumps(evidence or {}, ensure_ascii=False, default=str), int(priority))
            )
            pid = int(cur.lastrowid)
        return self.get(pid)

    def get(self, proposal_id):
        with self._connect() as c:
            row = c.execute("SELECT * FROM improvement_proposals WHERE id=?", (int(proposal_id),)).fetchone()
        if not row:
            return {"ok": False, "error": "Proposta não encontrada."}
        d = dict(row)
        try:
            d["evidence"] = json.loads(d.pop("evidence_json") or "{}")
        except Exception:
            d["evidence"] = {}
        return {"ok": True, "data": d}

    def list(self, status="proposed", limit=100):
        with self._connect() as c:
            rows = c.execute(
                "SELECT * FROM improvement_proposals WHERE status=? ORDER BY priority DESC,id DESC LIMIT ?",
                (str(status), int(limit))
            ).fetchall()
        items = []
        for row in rows:
            d = dict(row)
            try:
                d["evidence"] = json.loads(d.pop("evidence_json") or "{}")
            except Exception:
                d["evidence"] = {}
            items.append(d)
        return {"ok": True, "items": items, "count": len(items)}

    def resolve(self, proposal_id, status, note=""):
        if status not in {"accepted", "rejected", "implemented", "deferred"}:
            return {"ok": False, "error": "Status inválido."}
        with self._connect() as c:
            cur = c.execute(
                "UPDATE improvement_proposals SET status=?,resolution_note=? WHERE id=?",
                (status, str(note), int(proposal_id))
            )
        return {"ok": cur.rowcount > 0}

    def stats(self):
        with self._connect() as c:
            rows = c.execute("SELECT status,COUNT(*) n FROM improvement_proposals GROUP BY status").fetchall()
        return {"ok": True, "statuses": {x["status"]: x["n"] for x in rows}}
