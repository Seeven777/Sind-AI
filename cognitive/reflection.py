import re
import sqlite3
from collections import Counter
from datetime import datetime
from pathlib import Path


class ReflectionEngine:
    """
    Reflexão local e barata: identifica correções, padrões repetidos, falhas e
    oportunidades de Skill/automação sem precisar manter outro modelo rodando.
    """

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
            CREATE TABLE IF NOT EXISTS reflections(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              created_at TEXT NOT NULL,
              kind TEXT NOT NULL,
              trigger_text TEXT DEFAULT '',
              insight TEXT NOT NULL,
              confidence REAL NOT NULL DEFAULT .7,
              status TEXT NOT NULL DEFAULT 'active',
              occurrences INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS behavior_patterns(
              signature TEXT PRIMARY KEY,
              example TEXT NOT NULL,
              occurrences INTEGER NOT NULL DEFAULT 1,
              last_seen TEXT NOT NULL
            );
            """)

    def _signature(self, text):
        t = str(text or "").lower()
        tokens = re.findall(r"[a-zà-ÿ0-9_-]{3,}", t)
        stop = {"para","com","uma","que","dos","das","por","sobre","isso","essa","esse","meu","minha","mais","muito"}
        tokens = [x for x in tokens if x not in stop][:7]
        return " ".join(tokens)

    def _upsert_reflection(self, kind, trigger, insight, confidence=.75):
        with self._connect() as c:
            row = c.execute(
                "SELECT id,occurrences FROM reflections WHERE kind=? AND lower(insight)=lower(?) AND status='active'",
                (kind, insight)
            ).fetchone()
            if row:
                c.execute(
                    "UPDATE reflections SET occurrences=occurrences+1,confidence=min(1.0,confidence+.03) WHERE id=?",
                    (int(row["id"]),)
                )
                return int(row["id"])
            cur = c.execute(
                """INSERT INTO reflections(created_at,kind,trigger_text,insight,confidence,status)
                   VALUES(?,?,?,?,?,'active')""",
                (self._now(), kind, str(trigger), str(insight), float(confidence))
            )
            return int(cur.lastrowid)

    def reflect(self, user_text, answer="", status="completed", metadata=None):
        text = str(user_text or "").strip()
        results = []

        correction_markers = (
            "não gostei", "nao gostei", "não faça", "nao faca", "prefiro",
            "da próxima vez", "da proxima vez", "quero que", "evite", "sempre"
        )
        if any(x in text.lower() for x in correction_markers):
            rid = self._upsert_reflection(
                "correction",
                text,
                f"Levar em conta esta correção/preferência quando o contexto for semelhante: {text}",
                .88,
            )
            results.append(rid)

        signature = self._signature(text)
        if signature:
            with self._connect() as c:
                row = c.execute("SELECT occurrences FROM behavior_patterns WHERE signature=?", (signature,)).fetchone()
                if row:
                    count = int(row["occurrences"]) + 1
                    c.execute(
                        "UPDATE behavior_patterns SET occurrences=?,example=?,last_seen=? WHERE signature=?",
                        (count, text, self._now(), signature)
                    )
                else:
                    count = 1
                    c.execute(
                        "INSERT INTO behavior_patterns(signature,example,occurrences,last_seen) VALUES(?,?,?,?)",
                        (signature, text, count, self._now())
                    )
            if count == 3:
                rid = self._upsert_reflection(
                    "skill_candidate",
                    text,
                    f"A solicitação '{signature}' apareceu repetidamente. Avaliar transformar o processo em Skill ou rotina reutilizável.",
                    .72,
                )
                results.append(rid)

        if str(status).lower() != "completed":
            rid = self._upsert_reflection(
                "failure",
                text,
                f"Uma execução relacionada a '{signature or text[:80]}' falhou. Verificar fallback, timeout ou capacidade ausente antes de repetir.",
                .8,
            )
            results.append(rid)

        return {"ok": True, "reflection_ids": results, "pattern": signature}

    def relevant(self, query="", limit=8):
        terms = re.findall(r"[A-Za-zÀ-ÿ0-9_-]{3,}", str(query or "").lower())[:8]
        with self._connect() as c:
            rows = c.execute(
                "SELECT * FROM reflections WHERE status='active' ORDER BY confidence DESC,occurrences DESC,id DESC LIMIT 200"
            ).fetchall()
        scored = []
        for r in rows:
            d = dict(r)
            hay = (d["insight"] + " " + d.get("trigger_text","")).lower()
            score = sum(1 for t in terms if t in hay)
            if not terms or score:
                scored.append((score, d))
        scored.sort(key=lambda x: (-x[0], -x[1]["confidence"], -x[1]["occurrences"]))
        return [x[1] for x in scored[:int(limit)]]

    def list(self, kind=None, status="active", limit=100):
        sql = "SELECT * FROM reflections WHERE status=?"
        args = [str(status)]
        if kind:
            sql += " AND kind=?"
            args.append(str(kind))
        sql += " ORDER BY confidence DESC,occurrences DESC,id DESC LIMIT ?"
        args.append(int(limit))
        with self._connect() as c:
            rows = c.execute(sql, args).fetchall()
        return {"ok": True, "items": [dict(x) for x in rows], "count": len(rows)}

    def resolve(self, reflection_id):
        with self._connect() as c:
            cur = c.execute("UPDATE reflections SET status='resolved' WHERE id=?", (int(reflection_id),))
        return {"ok": cur.rowcount > 0}

    def stats(self):
        with self._connect() as c:
            active = c.execute("SELECT COUNT(*) n FROM reflections WHERE status='active'").fetchone()["n"]
            skills = c.execute("SELECT COUNT(*) n FROM reflections WHERE status='active' AND kind='skill_candidate'").fetchone()["n"]
            failures = c.execute("SELECT COUNT(*) n FROM reflections WHERE status='active' AND kind='failure'").fetchone()["n"]
        return {"ok": True, "active": active, "skill_candidates": skills, "failure_lessons": failures}
