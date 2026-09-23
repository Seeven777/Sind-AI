import json
import re
import sqlite3
import threading
import unicodedata
from datetime import datetime
from pathlib import Path


def _now():
    return datetime.now().isoformat(timespec="milliseconds")


def _norm(value):
    text = unicodedata.normalize("NFKD", str(value or "").lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9_.-]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokens(value):
    stop = {
        "a", "o", "as", "os", "um", "uma", "de", "da", "do", "das", "dos",
        "e", "em", "no", "na", "nos", "nas", "para", "por", "com", "sem",
        "como", "que", "eu", "voce", "você", "meu", "minha", "meus", "minhas",
    }
    return {x for x in _norm(value).replace("_", " ").split() if len(x) >= 2 and x not in stop}


class ProceduralMemory:
    """Persistent procedural memory for learned work routines.

    This store does not execute arbitrary code. It records *how* a task was learned,
    which applications were involved, what inputs are variable, and how mature the
    learned routine is. The executable implementation remains in the existing Skill/
    Action/Workflow layers.
    """

    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=20)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS procedures(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL UNIQUE,
                    source_kind TEXT NOT NULL DEFAULT 'demonstration',
                    source_ref TEXT DEFAULT '',
                    skill_name TEXT DEFAULT '',
                    app_ids_json TEXT NOT NULL DEFAULT '[]',
                    inputs_json TEXT NOT NULL DEFAULT '{}',
                    step_count INTEGER NOT NULL DEFAULT 0,
                    confidence REAL NOT NULL DEFAULT 0.35,
                    maturity TEXT NOT NULL DEFAULT 'learned',
                    success_count INTEGER NOT NULL DEFAULT 0,
                    correction_count INTEGER NOT NULL DEFAULT 0,
                    failure_count INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_used_at TEXT DEFAULT ''
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_procedures_updated ON procedures(updated_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_procedures_maturity ON procedures(maturity, updated_at DESC)"
            )

    @staticmethod
    def _decode(row):
        item = dict(row)
        for src, dst, default in (
            ("app_ids_json", "app_ids", []),
            ("inputs_json", "inputs", {}),
            ("metadata_json", "metadata", {}),
        ):
            raw = item.pop(src, None)
            try:
                item[dst] = json.loads(raw or json.dumps(default))
            except Exception:
                item[dst] = default
        return item

    @staticmethod
    def _maturity(success_count, correction_count, failure_count, confidence):
        total = int(success_count) + int(correction_count) + int(failure_count)
        if total >= 8 and success_count >= 6 and failure_count <= 1 and confidence >= 0.82:
            return "autonomous"
        if total >= 4 and success_count >= 3 and confidence >= 0.68:
            return "trusted"
        if total >= 1:
            return "practiced"
        return "learned"

    def remember_demonstration(
        self,
        name,
        source_session="",
        skill_name="",
        app_ids=None,
        inputs=None,
        step_count=0,
        metadata=None,
    ):
        clean_name = str(name or "").strip()
        if not clean_name:
            return {"ok": False, "error": "Nome da rotina não informado."}
        normalized = _norm(clean_name)
        apps = sorted({str(x).strip() for x in (app_ids or []) if str(x).strip()})
        payload_inputs = dict(inputs or {})
        meta = dict(metadata or {})
        now = _now()
        confidence = min(0.65, 0.38 + min(max(int(step_count), 0), 30) * 0.008)

        with self._lock, self._connect() as conn:
            current = conn.execute(
                "SELECT * FROM procedures WHERE normalized_name=?", (normalized,)
            ).fetchone()
            if current:
                current_decoded = self._decode(current)
                merged_apps = sorted(set(current_decoded.get("app_ids", [])) | set(apps))
                merged_inputs = dict(current_decoded.get("inputs") or {})
                merged_inputs.update(payload_inputs)
                merged_meta = dict(current_decoded.get("metadata") or {})
                merged_meta.update(meta)
                new_conf = max(float(current["confidence"] or 0.0), confidence)
                conn.execute(
                    """
                    UPDATE procedures SET
                        name=?, source_kind='demonstration', source_ref=?, skill_name=?,
                        app_ids_json=?, inputs_json=?, step_count=?, confidence=?,
                        metadata_json=?, updated_at=?
                    WHERE normalized_name=?
                    """,
                    (
                        clean_name,
                        str(source_session or current["source_ref"] or ""),
                        str(skill_name or current["skill_name"] or clean_name),
                        json.dumps(merged_apps, ensure_ascii=False),
                        json.dumps(merged_inputs, ensure_ascii=False, default=str),
                        max(int(step_count or 0), int(current["step_count"] or 0)),
                        new_conf,
                        json.dumps(merged_meta, ensure_ascii=False, default=str),
                        now,
                        normalized,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO procedures(
                        name, normalized_name, source_kind, source_ref, skill_name,
                        app_ids_json, inputs_json, step_count, confidence, maturity,
                        metadata_json, created_at, updated_at
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        clean_name,
                        normalized,
                        "demonstration",
                        str(source_session or ""),
                        str(skill_name or clean_name),
                        json.dumps(apps, ensure_ascii=False),
                        json.dumps(payload_inputs, ensure_ascii=False, default=str),
                        int(step_count or 0),
                        confidence,
                        "learned",
                        json.dumps(meta, ensure_ascii=False, default=str),
                        now,
                        now,
                    ),
                )
        item = self.get_by_name(clean_name)
        return {"ok": True, "procedure": item}

    def get_by_name(self, name):
        normalized = _norm(name)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM procedures WHERE normalized_name=?", (normalized,)
            ).fetchone()
        return self._decode(row) if row else None

    def list(self, limit=50, app_id=None):
        limit = max(1, min(int(limit), 500))
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM procedures ORDER BY updated_at DESC LIMIT ?", (limit * 3,)
            ).fetchall()
        items = [self._decode(row) for row in rows]
        if app_id:
            app_id = str(app_id)
            items = [x for x in items if app_id in (x.get("app_ids") or [])]
        return {"ok": True, "items": items[:limit], "count": len(items[:limit])}

    def search(self, query, limit=8, app_id=None):
        query_tokens = _tokens(query)
        listed = self.list(limit=250, app_id=app_id).get("items", [])
        ranked = []
        for item in listed:
            hay = " ".join(
                [
                    item.get("name", ""),
                    item.get("skill_name", ""),
                    " ".join(item.get("app_ids") or []),
                    json.dumps(item.get("metadata") or {}, ensure_ascii=False, default=str),
                ]
            )
            hay_norm = _norm(hay)
            hay_tokens = _tokens(hay)
            overlap = len(query_tokens & hay_tokens)
            score = overlap * 4
            normalized_query = _norm(query)
            if normalized_query and normalized_query in hay_norm:
                score += 10
            if app_id and app_id in (item.get("app_ids") or []):
                score += 4
            if not query_tokens and app_id:
                score += 1
            if score:
                ranked.append((score, item))
        ranked.sort(key=lambda x: (-x[0], x[1].get("name", "")))
        items = [item for _, item in ranked[: max(1, int(limit))]]
        return {"ok": True, "items": items, "count": len(items), "query": str(query or "")}

    def record_outcome(self, name, status="success", corrected=False):
        item = self.get_by_name(name)
        if not item:
            return {"ok": False, "error": "Rotina não encontrada."}

        success = int(item.get("success_count") or 0)
        corrections = int(item.get("correction_count") or 0)
        failures = int(item.get("failure_count") or 0)
        status = str(status or "success").strip().lower()
        if status in {"success", "completed", "ok"}:
            success += 1
        elif status in {"failed", "failure", "error"}:
            failures += 1
        if corrected:
            corrections += 1

        attempts = max(1, success + corrections + failures)
        raw = (success + 0.45 * corrections) / attempts
        confidence = max(0.15, min(0.98, 0.45 + 0.5 * raw - 0.06 * failures))
        maturity = self._maturity(success, corrections, failures, confidence)
        now = _now()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                UPDATE procedures SET success_count=?, correction_count=?, failure_count=?,
                    confidence=?, maturity=?, updated_at=?, last_used_at=?
                WHERE normalized_name=?
                """,
                (success, corrections, failures, confidence, maturity, now, now, _norm(name)),
            )
        return {"ok": True, "procedure": self.get_by_name(name)}

    def app_counts(self):
        counts = {}
        for item in self.list(limit=500).get("items", []):
            for app_id in item.get("app_ids") or []:
                counts[app_id] = counts.get(app_id, 0) + 1
        return counts

    def stats(self):
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN maturity='autonomous' THEN 1 ELSE 0 END) AS autonomous,
                       SUM(CASE WHEN maturity='trusted' THEN 1 ELSE 0 END) AS trusted,
                       SUM(CASE WHEN maturity='practiced' THEN 1 ELSE 0 END) AS practiced,
                       SUM(CASE WHEN maturity='learned' THEN 1 ELSE 0 END) AS learned
                FROM procedures
                """
            ).fetchone()
        return {
            "ok": True,
            "procedures": int(row["total"] or 0),
            "autonomous": int(row["autonomous"] or 0),
            "trusted": int(row["trusted"] or 0),
            "practiced": int(row["practiced"] or 0),
            "learned": int(row["learned"] or 0),
        }
