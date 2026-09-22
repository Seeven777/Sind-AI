import json
import sqlite3
from datetime import datetime
from pathlib import Path


class AttachmentManager:
    """Anexos de conversa/projeto indexados automaticamente na Knowledge Base."""

    SUPPORTED = {".txt",".md",".csv",".json",".log",".html",".htm",".pdf",".docx"}

    def __init__(self, db_path, knowledge, projects=None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge = knowledge
        self.projects = projects
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
            CREATE TABLE IF NOT EXISTS attachments(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              session_id INTEGER,
              project_id INTEGER,
              path TEXT NOT NULL,
              name TEXT NOT NULL,
              collection TEXT NOT NULL,
              document_id INTEGER,
              status TEXT NOT NULL,
              error TEXT,
              created_at TEXT NOT NULL
            )""")

    def _collection(self, session_id=None, project_id=None):
        if project_id:
            return f"project_{int(project_id)}"
        if session_id:
            return f"conversation_{int(session_id)}"
        return "attachments"

    def add_files(self, paths, session_id=None, project_id=None):
        items = []
        collection = self._collection(session_id, project_id)
        for raw in paths or []:
            p = Path(raw).expanduser().resolve()
            if not p.is_file():
                items.append({"ok": False, "path": str(p), "error": "Arquivo não encontrado."})
                continue
            if p.suffix.lower() not in self.SUPPORTED:
                items.append({"ok": False, "path": str(p), "error": f"Formato não suportado: {p.suffix}"})
                continue
            try:
                result = self.knowledge.ingest_file(collection, str(p), title=p.name)
                ok = bool(result.get("ok"))
                doc_id = result.get("document_id")
                error = result.get("error")
            except Exception as exc:
                ok, doc_id, error = False, None, str(exc)

            with self._connect() as c:
                cur = c.execute(
                    """INSERT INTO attachments(session_id,project_id,path,name,collection,document_id,status,error,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    (int(session_id) if session_id else None, int(project_id) if project_id else None,
                     str(p), p.name, collection, int(doc_id) if doc_id else None,
                     "ready" if ok else "failed", str(error) if error else None, self._now())
                )
                aid = int(cur.lastrowid)
            items.append({
                "ok": ok, "id": aid, "path": str(p), "name": p.name,
                "collection": collection, "document_id": doc_id, "error": error,
            })
        return {"ok": all(x.get("ok") for x in items) if items else True, "items": items, "count": len(items)}

    def list(self, session_id=None, project_id=None, limit=100):
        sql = "SELECT * FROM attachments WHERE 1=1"
        args = []
        if session_id is not None and project_id is not None:
            sql += " AND (session_id=? OR project_id=?)"
            args.extend([int(session_id), int(project_id)])
        elif session_id is not None:
            sql += " AND session_id=?"
            args.append(int(session_id))
        elif project_id is not None:
            sql += " AND project_id=?"
            args.append(int(project_id))
        sql += " ORDER BY id DESC LIMIT ?"
        args.append(int(limit))
        with self._connect() as c:
            rows = c.execute(sql, args).fetchall()
        return {"ok": True, "items": [dict(x) for x in rows], "count": len(rows)}

    def search_context(self, query, session_id=None, project_id=None, limit=5, max_chars=2600):
        collections = []
        if session_id:
            collections.append(self._collection(session_id=session_id))
        if project_id:
            collections.append(self._collection(project_id=project_id))

        # FTS5 can behave like AND for natural multi-word queries. Relax the
        # search progressively so a relevant attachment is not lost because one
        # unrelated term came from the surrounding conversation.
        raw = str(query or "").strip()
        tokens = [
            x for x in __import__("re").findall(r"[A-Za-zÀ-ÿ0-9_-]{3,}", raw)
            if x.lower() not in {
                "para","com","uma","que","dos","das","por","sobre","isso","essa",
                "esse","mais","muito","projeto","conversa"
            }
        ]
        variants = [raw] + tokens[:6]

        found = []
        seen = set()
        for collection in collections:
            for variant in variants:
                if not variant:
                    continue
                try:
                    r = self.knowledge.search(collection, variant, limit=limit)
                except Exception:
                    continue
                for item in r.get("items", []):
                    key = (collection, item.get("document_id"), item.get("chunk_id"))
                    if key in seen:
                        continue
                    seen.add(key)
                    found.append({**item, "collection": collection, "matched_query": variant})
                    if len(found) >= int(limit):
                        break
                if len(found) >= int(limit):
                    break
            if len(found) >= int(limit):
                break

        text_parts = []
        for item in found:
            text_parts.append(
                f"[ANEXO:{item.get('collection')}/doc:{item.get('document_id')}/chunk:{item.get('chunk_id')}]\n"
                f"{item.get('title','')}\n{item.get('text','')}"
            )
        return {"ok": True, "items": found, "text": "\n\n".join(text_parts)[:int(max_chars)]}

    def stats(self):
        with self._connect() as c:
            total = c.execute("SELECT COUNT(*) n FROM attachments").fetchone()["n"]
            ready = c.execute("SELECT COUNT(*) n FROM attachments WHERE status='ready'").fetchone()["n"]
        return {"ok": True, "attachments": total, "ready": ready}
