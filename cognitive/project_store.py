import json
import sqlite3
from datetime import datetime
from pathlib import Path


class ProjectStore:
    """Projetos persistentes que agrupam conversas, notas, arquivos e contexto."""

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
            c.executescript("""
            CREATE TABLE IF NOT EXISTS projects(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE,
              description TEXT DEFAULT '',
              status TEXT NOT NULL DEFAULT 'active',
              root_path TEXT DEFAULT '',
              metadata_json TEXT NOT NULL DEFAULT '{}',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS project_sessions(
              project_id INTEGER NOT NULL,
              session_id INTEGER NOT NULL,
              linked_at TEXT NOT NULL,
              UNIQUE(project_id, session_id)
            );
            CREATE TABLE IF NOT EXISTS project_notes(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              project_id INTEGER NOT NULL,
              title TEXT NOT NULL,
              body TEXT NOT NULL,
              tags TEXT DEFAULT '',
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS project_state(
              key TEXT PRIMARY KEY,
              value TEXT NOT NULL,
              updated_at TEXT NOT NULL
            );
            """)

    def _project(self, row):
        if not row:
            return None
        d = dict(row)
        try:
            d["metadata"] = json.loads(d.pop("metadata_json") or "{}")
        except Exception:
            d["metadata"] = {}
        return d

    def create(self, name, description="", root_path="", metadata=None):
        name = str(name).strip()
        if not name:
            return {"ok": False, "error": "Nome do projeto é obrigatório."}
        now = self._now()
        try:
            with self._connect() as c:
                cur = c.execute(
                    """INSERT INTO projects(name,description,status,root_path,metadata_json,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?)""",
                    (name, str(description), "active", str(root_path or ""),
                     json.dumps(metadata or {}, ensure_ascii=False), now, now)
                )
                pid = int(cur.lastrowid)
        except sqlite3.IntegrityError:
            return {"ok": False, "error": f"Já existe projeto chamado '{name}'."}
        self.set_current(pid)
        return self.get(pid)

    def get(self, project_id):
        with self._connect() as c:
            row = c.execute("SELECT * FROM projects WHERE id=?", (int(project_id),)).fetchone()
        return {"ok": bool(row), "data": self._project(row), "error": None if row else "Projeto não encontrado."}

    def list(self, status=None, limit=100):
        sql = "SELECT * FROM projects"
        args = []
        if status:
            sql += " WHERE status=?"
            args.append(str(status))
        sql += " ORDER BY updated_at DESC LIMIT ?"
        args.append(int(limit))
        with self._connect() as c:
            rows = c.execute(sql, args).fetchall()
        return {"ok": True, "items": [self._project(x) for x in rows], "count": len(rows), "current": self.current_id()}

    def update(self, project_id, **fields):
        sets, args = [], []
        for key in ("name", "description", "status", "root_path"):
            if key in fields and fields[key] is not None:
                sets.append(f"{key}=?")
                args.append(str(fields[key]))
        if "metadata" in fields and fields["metadata"] is not None:
            sets.append("metadata_json=?")
            args.append(json.dumps(fields["metadata"], ensure_ascii=False))
        if not sets:
            return self.get(project_id)
        sets.append("updated_at=?")
        args.extend([self._now(), int(project_id)])
        with self._connect() as c:
            c.execute(f"UPDATE projects SET {','.join(sets)} WHERE id=?", args)
        return self.get(project_id)

    def archive(self, project_id):
        return self.update(project_id, status="archived")

    def set_current(self, project_id=None):
        value = "" if project_id in (None, "", 0) else str(int(project_id))
        with self._connect() as c:
            c.execute(
                """INSERT INTO project_state(key,value,updated_at) VALUES('current_project',?,?)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
                (value, self._now())
            )
        return {"ok": True, "current": int(value) if value else None}

    def current_id(self):
        with self._connect() as c:
            row = c.execute("SELECT value FROM project_state WHERE key='current_project'").fetchone()
        try:
            return int(row["value"]) if row and row["value"] else None
        except Exception:
            return None

    def current(self):
        pid = self.current_id()
        if not pid:
            return {"ok": True, "data": None}
        return self.get(pid)

    def link_session(self, project_id, session_id):
        with self._connect() as c:
            c.execute(
                "INSERT OR IGNORE INTO project_sessions(project_id,session_id,linked_at) VALUES(?,?,?)",
                (int(project_id), int(session_id), self._now())
            )
            c.execute("UPDATE projects SET updated_at=? WHERE id=?", (self._now(), int(project_id)))
        return {"ok": True, "project_id": int(project_id), "session_id": int(session_id)}

    def sessions(self, project_id):
        with self._connect() as c:
            rows = c.execute(
                "SELECT session_id,linked_at FROM project_sessions WHERE project_id=? ORDER BY linked_at DESC",
                (int(project_id),)
            ).fetchall()
        return {"ok": True, "items": [dict(x) for x in rows], "count": len(rows)}


    def unlink_session(self, session_id, project_id=None):
        with self._connect() as c:
            if project_id:
                cur = c.execute(
                    "DELETE FROM project_sessions WHERE project_id=? AND session_id=?",
                    (int(project_id), int(session_id))
                )
            else:
                cur = c.execute(
                    "DELETE FROM project_sessions WHERE session_id=?",
                    (int(session_id),)
                )
        return {"ok": True, "session_id": int(session_id), "unlinked": int(cur.rowcount)}

    def add_note(self, project_id, title, body, tags=None):
        now = self._now()
        with self._connect() as c:
            cur = c.execute(
                """INSERT INTO project_notes(project_id,title,body,tags,created_at,updated_at)
                   VALUES(?,?,?,?,?,?)""",
                (int(project_id), str(title).strip() or "Nota", str(body),
                 ",".join(tags or []) if isinstance(tags, list) else str(tags or ""), now, now)
            )
            nid = int(cur.lastrowid)
        return {"ok": True, "id": nid, "project_id": int(project_id)}

    def notes(self, project_id, query=None, limit=50):
        sql = "SELECT * FROM project_notes WHERE project_id=?"
        args = [int(project_id)]
        if query:
            sql += " AND (title LIKE ? OR body LIKE ? OR tags LIKE ?)"
            q = f"%{str(query)}%"
            args += [q, q, q]
        sql += " ORDER BY updated_at DESC LIMIT ?"
        args.append(int(limit))
        with self._connect() as c:
            rows = c.execute(sql, args).fetchall()
        return {"ok": True, "items": [dict(x) for x in rows], "count": len(rows)}

    def context(self, query="", max_chars=2400):
        current = self.current().get("data")
        if not current:
            return {"ok": True, "text": "", "project": None}
        notes = self.notes(current["id"], query=query or None, limit=8).get("items", [])
        chunks = [
            f"PROJETO ATUAL: {current['name']}",
            f"Descrição: {current.get('description','')}",
        ]
        for n in notes:
            chunks.append(f"Nota — {n['title']}: {n['body']}")
        text = "\n".join(x for x in chunks if x.strip())[:int(max_chars)]
        return {"ok": True, "text": text, "project": current}

    def stats(self):
        with self._connect() as c:
            projects = c.execute("SELECT COUNT(*) n FROM projects WHERE status='active'").fetchone()["n"]
            notes = c.execute("SELECT COUNT(*) n FROM project_notes").fetchone()["n"]
            links = c.execute("SELECT COUNT(*) n FROM project_sessions").fetchone()["n"]
        return {"ok": True, "projects": projects, "notes": notes, "session_links": links, "current": self.current_id()}
