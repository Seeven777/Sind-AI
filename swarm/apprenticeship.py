import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ApprenticeshipEngine:
    """Ensino persistente de rotinas em linguagem natural, sem exigir código do usuário."""

    START_PATTERNS = (
        r"^vou te ensinar(?: a| como)?\s+(.+)$",
        r"^quero te ensinar(?: a| como)?\s+(.+)$",
        r"^aprenda comigo(?: a| como)?\s+(.+)$",
        r"^modo ensino[:\s]+(.+)$",
    )
    FINISH_MARKERS = (
        "finalizar ensino", "terminei de ensinar", "fim do ensinamento",
        "pode salvar essa rotina", "salve essa rotina", "encerre o ensino",
    )
    CANCEL_MARKERS = ("cancelar ensino", "cancele o ensino", "abortar ensino")

    def __init__(self, db_path, models=None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.models = models
        self._active = None
        self._init_db()
        self._resume_open()

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
                CREATE TABLE IF NOT EXISTS procedures(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    trigger_text TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    steps_json TEXT NOT NULL DEFAULT '[]',
                    examples_json TEXT NOT NULL DEFAULT '[]',
                    confidence REAL NOT NULL DEFAULT 0.65,
                    uses INTEGER NOT NULL DEFAULT 0,
                    successes INTEGER NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS teaching_notes(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    notes_json TEXT NOT NULL DEFAULT '[]',
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    def _resume_open(self):
        try:
            with self._connect() as c:
                row = c.execute(
                    "SELECT * FROM teaching_notes WHERE status='open' ORDER BY id DESC LIMIT 1"
                ).fetchone()
            if not row:
                return
            try:
                notes = json.loads(row["notes_json"] or "[]")
            except Exception:
                notes = []
            self._active = {"id": int(row["id"]), "title": row["title"], "notes": notes}
        except Exception:
            self._active = None

    def _start_match(self, text):
        raw = str(text or "").strip()
        for pattern in self.START_PATTERNS:
            m = re.match(pattern, raw, flags=re.I)
            if m:
                return m.group(1).strip(" .:;\n\t")
        return None

    def active(self):
        return dict(self._active) if self._active else None

    def _save_active(self):
        if not self._active:
            return
        now = self._now()
        with self._connect() as c:
            if self._active.get("id"):
                c.execute(
                    "UPDATE teaching_notes SET notes_json=?,updated_at=? WHERE id=?",
                    (json.dumps(self._active["notes"], ensure_ascii=False), now, int(self._active["id"])),
                )
            else:
                cur = c.execute(
                    "INSERT INTO teaching_notes(title,notes_json,status,created_at,updated_at) VALUES(?,?,?,?,?)",
                    (
                        self._active["title"], json.dumps(self._active["notes"], ensure_ascii=False),
                        "open", now, now,
                    ),
                )
                self._active["id"] = int(cur.lastrowid)

    def _normalize_steps(self, text, notes):
        steps = []
        for line in str(text or "").splitlines():
            line = re.sub(r"^\s*(?:\d+[.)]|[-*•])\s*", "", line).strip()
            if line and len(line) > 3:
                steps.append(line)
        if len(steps) < 2:
            steps = [str(x).strip() for x in notes if str(x).strip()]
        return steps[:30]

    def _compile(self, title, notes):
        description = f"Rotina ensinada pelo usuário para: {title}."
        steps = list(notes)
        if self.models and notes:
            prompt = (
                "Transforme as anotações abaixo em um procedimento operacional reutilizável. "
                "Responda APENAS com passos curtos, um por linha, sem introdução e sem chain-of-thought.\n\n"
                f"Objetivo: {title}\nANOTAÇÕES:\n" + "\n".join(f"- {n}" for n in notes)
            )
            try:
                resp = self.models.chat(
                    [
                        {"role": "system", "content": "Você compila ensinamentos do usuário em procedimentos claros e fiéis."},
                        {"role": "user", "content": prompt},
                    ],
                    user_text=title,
                    force="fast",
                )
                content = (resp.get("message") or {}).get("content", "")
                parsed = self._normalize_steps(content, notes)
                if parsed:
                    steps = parsed
            except Exception:
                steps = list(notes)
        return description, steps

    def _finalize(self):
        if not self._active:
            return {"ok": False, "handled": True, "answer": "Não há um ensino em andamento."}
        title = self._active["title"]
        notes = list(self._active["notes"])
        if not notes:
            return {"ok": False, "handled": True, "answer": "Ainda não recebi passos suficientes para salvar essa rotina."}
        description, steps = self._compile(title, notes)
        now = self._now()
        with self._connect() as c:
            cur = c.execute(
                "INSERT INTO procedures(name,trigger_text,description,steps_json,examples_json,confidence,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    title, title, description,
                    json.dumps(steps, ensure_ascii=False),
                    json.dumps(notes[-5:], ensure_ascii=False),
                    0.72, now, now,
                ),
            )
            proc_id = int(cur.lastrowid)
            if self._active.get("id"):
                c.execute(
                    "UPDATE teaching_notes SET status='compiled',updated_at=? WHERE id=?",
                    (now, int(self._active["id"])),
                )
        self._active = None
        return {
            "ok": True, "handled": True, "procedure_id": proc_id,
            "answer": f"Aprendi a rotina “{title}” com {len(steps)} passo(s). Vou reutilizá-la quando um pedido semelhante aparecer.",
        }

    def handle(self, text):
        raw = str(text or "").strip()
        low = raw.lower()

        if any(marker in low for marker in self.CANCEL_MARKERS):
            if self._active and self._active.get("id"):
                with self._connect() as c:
                    c.execute(
                        "UPDATE teaching_notes SET status='cancelled',updated_at=? WHERE id=?",
                        (self._now(), int(self._active["id"])),
                    )
            self._active = None
            return {"ok": True, "handled": True, "answer": "Ensino cancelado."}

        if any(marker in low for marker in self.FINISH_MARKERS):
            return self._finalize()

        if any(x in low for x in ("o que eu te ensinei", "liste rotinas aprendidas", "rotinas que você aprendeu", "procedimentos aprendidos")):
            items = self.list(limit=30).get("items", [])
            if not items:
                return {"ok": True, "handled": True, "answer": "Ainda não tenho rotinas ensinadas salvas."}
            lines = [f"• {x['name']} — {len(x.get('steps', []))} passo(s), usada {x.get('uses',0)} vez(es)" for x in items]
            return {"ok": True, "handled": True, "answer": "Rotinas aprendidas:\n" + "\n".join(lines)}

        title = self._start_match(raw)
        if title:
            self._active = {"id": None, "title": title, "notes": []}
            self._save_active()
            return {
                "ok": True, "handled": True,
                "answer": (
                    f"Modo de ensino iniciado para “{title}”. Explique os passos, regras, exceções e exemplos como você faria na prática. "
                    "Vou anotar cada mensagem. Quando terminar, diga “finalizar ensino”."
                ),
            }

        if self._active:
            self._active["notes"].append(raw)
            self._save_active()
            return {
                "ok": True, "handled": True,
                "answer": f"Anotado como parte do ensino de “{self._active['title']}” (item {len(self._active['notes'])}). Continue ou diga “finalizar ensino”.",
            }

        return {"ok": True, "handled": False}

    def _decode(self, row):
        d = dict(row)
        for key in ("steps_json", "examples_json"):
            try:
                d[key[:-5]] = json.loads(d.get(key) or "[]")
            except Exception:
                d[key[:-5]] = []
        return d

    def list(self, limit=50):
        with self._connect() as c:
            rows = c.execute(
                "SELECT * FROM procedures WHERE status='active' ORDER BY updated_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        items = [self._decode(r) for r in rows]
        return {"ok": True, "items": items, "count": len(items)}

    def relevant(self, query, limit=3):
        q = str(query or "").lower()
        tokens = set(re.findall(r"[a-zà-ÿ0-9_-]{3,}", q))
        scored = []
        for item in self.list(limit=100)["items"]:
            hay = " ".join([
                item.get("name", ""), item.get("trigger_text", ""), item.get("description", ""),
                " ".join(item.get("steps", [])),
            ]).lower()
            score = 0
            if item.get("trigger_text", "").lower() in q:
                score += 10
            score += sum(1 for token in tokens if token in hay)
            if score >= 2:
                scored.append((score, item))
        scored.sort(key=lambda x: (-x[0], -float(x[1].get("confidence", 0)), x[1]["id"]))
        return [item for _, item in scored[:int(limit)]]

    def context(self, query, limit=2, max_chars=2600):
        items = self.relevant(query, limit=limit)
        parts = []
        for item in items:
            steps = "\n".join(f"{i+1}. {step}" for i, step in enumerate(item.get("steps", [])))
            parts.append(f"PROCEDIMENTO ENSINADO: {item['name']}\n{steps}")
        return {"items": items, "text": "\n\n".join(parts)[:int(max_chars)]}

    def record_use(self, procedure_ids, success=True):
        ids = [int(x) for x in procedure_ids or [] if str(x).isdigit() or isinstance(x, int)]
        if not ids:
            return
        with self._connect() as c:
            for pid in ids:
                if success:
                    c.execute(
                        "UPDATE procedures SET uses=uses+1,successes=successes+1,confidence=MIN(0.98,confidence+0.02),updated_at=? WHERE id=?",
                        (self._now(), pid),
                    )
                else:
                    c.execute(
                        "UPDATE procedures SET uses=uses+1,confidence=MAX(0.20,confidence-0.04),updated_at=? WHERE id=?",
                        (self._now(), pid),
                    )

    def stats(self):
        with self._connect() as c:
            row = c.execute(
                "SELECT COUNT(*) procedures,COALESCE(SUM(uses),0) uses,COALESCE(SUM(successes),0) successes FROM procedures WHERE status='active'"
            ).fetchone()
        return {"ok": True, **dict(row), "teaching_active": bool(self._active)}
