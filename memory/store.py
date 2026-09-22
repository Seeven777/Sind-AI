import re
import sqlite3
from datetime import datetime
from pathlib import Path


STOPWORDS = {
    "a","o","as","os","de","da","do","das","dos","e","em","no","na","nos","nas",
    "um","uma","para","por","que","eu","meu","minha","meus","minhas","quando",
    "como","qual","quais","isso","isto","ser","é","eh","ao","à","aos","às"
}


class MemoryStore:
    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL DEFAULT 'fact',
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_memories_key
                ON memories(key);

                CREATE TABLE IF NOT EXISTS aliases (
                    alias TEXT PRIMARY KEY COLLATE NOCASE,
                    target TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

    def remember(self, value, key=None, kind="fact"):
        value = str(value).strip()
        key = (key or value[:120]).strip()
        now = datetime.now().isoformat(timespec="seconds")

        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM memories WHERE lower(key)=lower(?)",
                (key,)
            ).fetchone()

            if row:
                conn.execute(
                    "UPDATE memories SET value=?, kind=?, updated_at=? WHERE id=?",
                    (value, kind, now, row["id"])
                )
                memory_id = row["id"]
            else:
                cur = conn.execute(
                    "INSERT INTO memories(kind,key,value,created_at,updated_at) VALUES(?,?,?,?,?)",
                    (kind, key, value, now, now)
                )
                memory_id = cur.lastrowid

        return {"ok": True, "id": memory_id, "key": key, "value": value}

    def set_alias(self, alias, target):
        alias = str(alias).strip().strip('"').strip("'")
        target = str(target).strip().strip('"').strip("'")
        now = datetime.now().isoformat(timespec="seconds")

        with self._connect() as conn:
            conn.execute("""
                INSERT INTO aliases(alias,target,created_at,updated_at)
                VALUES(?,?,?,?)
                ON CONFLICT(alias) DO UPDATE SET
                    target=excluded.target,
                    updated_at=excluded.updated_at
            """, (alias, target, now, now))

        return {"ok": True, "alias": alias, "target": target}

    def list_aliases(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT alias,target FROM aliases ORDER BY alias COLLATE NOCASE"
            ).fetchall()
        return [dict(r) for r in rows]

    def list_memories(self, limit=100):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id,kind,key,value,created_at,updated_at "
                "FROM memories ORDER BY updated_at DESC LIMIT ?",
                (int(limit),)
            ).fetchall()
        return [dict(r) for r in rows]

    def count(self):
        with self._connect() as conn:
            m = conn.execute("SELECT COUNT(*) AS n FROM memories").fetchone()["n"]
            a = conn.execute("SELECT COUNT(*) AS n FROM aliases").fetchone()["n"]
        return {"memories": m, "aliases": a}

    def forget(self, query):
        query = str(query).strip().rstrip(" .!?;,:")
        qtokens = self._tokens(query)

        memory_ids = []
        alias_names = []

        for item in self.list_memories(limit=1000):
            text = f"{item['key']} {item['value']}"
            low = text.lower()
            overlap = len(qtokens & self._tokens(text))

            if query.lower() in low or (qtokens and overlap >= max(1, len(qtokens) // 2)):
                memory_ids.append(item["id"])

        for item in self.list_aliases():
            text = f"{item['alias']} {item['target']}"
            low = text.lower()
            overlap = len(qtokens & self._tokens(text))

            if query.lower() in low or (qtokens and overlap >= max(1, len(qtokens) // 2)):
                alias_names.append(item["alias"])

        with self._connect() as conn:
            for memory_id in memory_ids:
                conn.execute("DELETE FROM memories WHERE id=?", (memory_id,))
            for alias in alias_names:
                conn.execute("DELETE FROM aliases WHERE alias=?", (alias,))

        return {
            "ok": True,
            "deleted_memories": len(memory_ids),
            "deleted_aliases": len(alias_names),
        }

    def _tokens(self, text):
        words = re.findall(r"[A-Za-zÀ-ÿ0-9_:\\.-]+", str(text).lower())
        return {w for w in words if len(w) >= 3 and w not in STOPWORDS}

    def relevant(self, query, limit=6):
        qtokens = self._tokens(query)
        scored = []

        for item in self.list_memories(limit=300):
            text = f"{item['key']} {item['value']}"
            tokens = self._tokens(text)
            overlap = len(qtokens & tokens)
            phrase_bonus = 3 if str(query).lower() in text.lower() else 0
            score = overlap + phrase_bonus
            if score > 0:
                scored.append((score, item))

        for alias in self.list_aliases():
            text = f"{alias['alias']} {alias['target']}"
            tokens = self._tokens(text)
            overlap = len(qtokens & tokens)
            phrase_bonus = 4 if alias["alias"].lower() in str(query).lower() else 0
            score = overlap + phrase_bonus
            if score > 0:
                scored.append((
                    score,
                    {
                        "kind": "alias",
                        "key": alias["alias"],
                        "value": alias["target"],
                    }
                ))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:limit]]

    def resolve_alias(self, raw):
        """
        Resolve aliases de caminho sem usar LLM.

        Ex:
          "pasta do trabalho" -> D:\\Trabalho
          "pasta do trabalho\\relatorio.xlsx" -> D:\\Trabalho\\relatorio.xlsx
        """
        if raw is None:
            return raw

        original = str(raw).strip()

        aliases = sorted(
            self.list_aliases(),
            key=lambda x: len(x["alias"]),
            reverse=True
        )

        low = original.lower()

        for item in aliases:
            alias = item["alias"].strip()
            target = item["target"].strip()

            if low == alias.lower():
                return target

            for sep in ("\\", "/"):
                prefix = alias.lower() + sep
                if low.startswith(prefix):
                    remainder = original[len(alias):].lstrip("\\/")
                    return str(Path(target) / remainder)

        return original
