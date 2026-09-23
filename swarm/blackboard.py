import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class SwarmBlackboard:
    """Memória compartilhada por uma execução multiagente, persistida para auditoria/aprendizado."""

    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _now(self):
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def _init_db(self):
        with self._connect() as c:
            c.executescript(
                """
                CREATE TABLE IF NOT EXISTS swarm_sessions(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'running',
                    roles_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS swarm_entries(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    agent TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES swarm_sessions(id)
                );
                CREATE INDEX IF NOT EXISTS idx_swarm_entries_session ON swarm_entries(session_id,id);
                """
            )

    def start(self, goal, roles=None):
        now = self._now()
        roles = list(roles or [])
        with self._connect() as c:
            cur = c.execute(
                "INSERT INTO swarm_sessions(goal,status,roles_json,created_at,updated_at) VALUES(?,?,?,?,?)",
                (str(goal), "running", json.dumps(roles, ensure_ascii=False), now, now),
            )
            return int(cur.lastrowid)

    def add(self, session_id, agent, kind, content, metadata=None):
        now = self._now()
        with self._connect() as c:
            cur = c.execute(
                "INSERT INTO swarm_entries(session_id,agent,kind,content,metadata_json,created_at) VALUES(?,?,?,?,?,?)",
                (
                    int(session_id), str(agent), str(kind), str(content),
                    json.dumps(metadata or {}, ensure_ascii=False), now,
                ),
            )
            c.execute("UPDATE swarm_sessions SET updated_at=? WHERE id=?", (now, int(session_id)))
            return int(cur.lastrowid)

    def finish(self, session_id, status="completed"):
        with self._connect() as c:
            c.execute(
                "UPDATE swarm_sessions SET status=?, updated_at=? WHERE id=?",
                (str(status), self._now(), int(session_id)),
            )
        return {"ok": True, "session_id": int(session_id), "status": status}

    def entries(self, session_id, limit=50):
        with self._connect() as c:
            rows = c.execute(
                "SELECT * FROM swarm_entries WHERE session_id=? ORDER BY id ASC LIMIT ?",
                (int(session_id), int(limit)),
            ).fetchall()
        return [dict(r) for r in rows]

    def context(self, session_id, max_chars=5000):
        chunks = []
        for row in self.entries(session_id, limit=30):
            chunks.append(f"[{row['agent']} / {row['kind']}]\n{row['content']}")
        return "\n\n".join(chunks)[-int(max_chars):]

    def stats(self):
        with self._connect() as c:
            sessions = c.execute("SELECT COUNT(*) n FROM swarm_sessions").fetchone()["n"]
            entries = c.execute("SELECT COUNT(*) n FROM swarm_entries").fetchone()["n"]
            active = c.execute("SELECT COUNT(*) n FROM swarm_sessions WHERE status='running'").fetchone()["n"]
        return {"ok": True, "sessions": sessions, "entries": entries, "active": active}
