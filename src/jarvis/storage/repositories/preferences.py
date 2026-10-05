from __future__ import annotations
import json
from datetime import datetime, timezone


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class PreferenceRepository:
    """Small persistent JSON preferences store backed by system_kv."""
    PREFIX = "ui.preference."

    def __init__(self, conn):
        self.conn = conn

    def get(self, key: str, default=None):
        row = self.conn.execute(
            "SELECT value_json FROM system_kv WHERE key=?",
            (self.PREFIX + key,),
        ).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value_json"])
        except Exception:
            return default

    def all(self) -> dict:
        rows = self.conn.execute(
            "SELECT key,value_json FROM system_kv WHERE key LIKE ? ORDER BY key",
            (self.PREFIX + "%",),
        ).fetchall()
        result = {}
        for row in rows:
            key = str(row["key"])[len(self.PREFIX):]
            try:
                result[key] = json.loads(row["value_json"])
            except Exception:
                continue
        return result

    def set(self, key: str, value) -> dict:
        safe_key = str(key).strip()
        if not safe_key or len(safe_key) > 120:
            raise ValueError("Chave de preferência inválida.")
        encoded = json.dumps(value, ensure_ascii=False)
        if len(encoded) > 64_000:
            raise ValueError("Preferência excede o tamanho permitido.")
        self.conn.execute(
            "INSERT INTO system_kv(key,value_json,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at",
            (self.PREFIX + safe_key, encoded, now()),
        )
        self.conn.commit()
        return {"key": safe_key, "value": value}

    def update(self, values: dict) -> dict:
        if not isinstance(values, dict):
            raise ValueError("Preferências precisam ser um objeto.")
        for key, value in values.items():
            self.set(key, value)
        return self.all()

    def delete(self, key: str) -> bool:
        cur = self.conn.execute(
            "DELETE FROM system_kv WHERE key=?",
            (self.PREFIX + str(key).strip(),),
        )
        self.conn.commit()
        return cur.rowcount > 0
