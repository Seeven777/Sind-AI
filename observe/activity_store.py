import json
import sqlite3
import threading
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path


class ActivityStore:
    """Persistent event ledger for low-cost personal context observation.

    The store is intentionally generic. It can receive OS/window events today and,
    later, structured events from Photoshop/VSCode/browser bridges without changing
    the database contract.
    """

    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=20)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    @staticmethod
    def _now():
        return datetime.now().isoformat(timespec="milliseconds")

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_events(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    source TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    app_id TEXT DEFAULT '',
                    process_name TEXT DEFAULT '',
                    window_title TEXT DEFAULT '',
                    session_id TEXT DEFAULT '',
                    dedupe_key TEXT DEFAULT '',
                    payload_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_events_ts ON activity_events(ts DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_events_app ON activity_events(app_id, ts DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_activity_events_type ON activity_events(event_type, ts DESC)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS activity_settings(
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def set_setting(self, key, value):
        payload = json.dumps(value, ensure_ascii=False, default=str)
        with self._write_lock, self._connect() as conn:
            conn.execute(
                """
                INSERT INTO activity_settings(key, value_json, updated_at)
                VALUES(?,?,?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json=excluded.value_json,
                    updated_at=excluded.updated_at
                """,
                (str(key), payload, self._now()),
            )

    def get_setting(self, key, default=None):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT value_json FROM activity_settings WHERE key=?", (str(key),)
            ).fetchone()
        if not row:
            return default
        try:
            return json.loads(row["value_json"])
        except Exception:
            return default

    def record(self, event):
        event = dict(event or {})
        payload = event.get("payload") or {}
        with self._write_lock, self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO activity_events(
                    ts, source, event_type, app_id, process_name, window_title,
                    session_id, dedupe_key, payload_json
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (
                    str(event.get("ts") or self._now()),
                    str(event.get("source") or "observer"),
                    str(event.get("event_type") or "event"),
                    str(event.get("app_id") or ""),
                    str(event.get("process_name") or ""),
                    str(event.get("window_title") or ""),
                    str(event.get("session_id") or ""),
                    str(event.get("dedupe_key") or ""),
                    json.dumps(payload, ensure_ascii=False, default=str),
                ),
            )
            event_id = int(cur.lastrowid)
        return event_id

    @staticmethod
    def _decode_row(row):
        item = dict(row)
        try:
            item["payload"] = json.loads(item.pop("payload_json") or "{}")
        except Exception:
            item["payload"] = {}
        return item

    def recent(self, minutes=30, limit=200, event_types=None):
        minutes = max(1, int(minutes))
        limit = max(1, min(int(limit), 2000))
        cutoff = (datetime.now() - timedelta(minutes=minutes)).isoformat(timespec="milliseconds")
        params = [cutoff]
        where = "ts >= ?"
        if event_types:
            values = [str(x) for x in event_types if str(x).strip()]
            if values:
                where += " AND event_type IN (%s)" % ",".join("?" for _ in values)
                params.extend(values)
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT * FROM activity_events WHERE {where} ORDER BY id DESC LIMIT ?",
                tuple(params),
            ).fetchall()
        return [self._decode_row(row) for row in rows]

    def latest(self):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM activity_events ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return self._decode_row(row) if row else None

    def count(self):
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM activity_events").fetchone()
        return int(row["n"] if row else 0)

    def summary(self, minutes=60, limit=1000):
        items = list(reversed(self.recent(minutes=minutes, limit=limit)))
        app_counter = Counter()
        type_counter = Counter()
        transitions = Counter()
        previous_app = None

        for item in items:
            app_id = (item.get("app_id") or "unknown").strip() or "unknown"
            event_type = (item.get("event_type") or "event").strip() or "event"
            app_counter[app_id] += 1
            type_counter[event_type] += 1
            if event_type == "window_focus":
                if previous_app and previous_app != app_id:
                    transitions[(previous_app, app_id)] += 1
                previous_app = app_id

        return {
            "ok": True,
            "minutes": int(minutes),
            "events": len(items),
            "apps": dict(app_counter.most_common(12)),
            "event_types": dict(type_counter.most_common(12)),
            "transitions": [
                {"from": src, "to": dst, "count": count}
                for (src, dst), count in transitions.most_common(12)
            ],
        }

    def prune(self, days=30):
        days = max(1, int(days))
        cutoff = (datetime.now() - timedelta(days=days)).isoformat(timespec="milliseconds")
        with self._write_lock, self._connect() as conn:
            cur = conn.execute("DELETE FROM activity_events WHERE ts < ?", (cutoff,))
        return {"ok": True, "deleted": int(cur.rowcount or 0), "days": days}
