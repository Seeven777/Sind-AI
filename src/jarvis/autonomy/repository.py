from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _loads(value, default):
    try:
        return json.loads(value or "")
    except Exception:
        return default


class AutonomyRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_state(self, key: str, default=None):
        row = self.conn.execute(
            "SELECT value_json FROM autonomy_state WHERE key=?", (str(key),)
        ).fetchone()
        return default if row is None else _loads(row["value_json"], default)

    def set_state(self, key: str, value):
        ts = now()
        self.conn.execute(
            "INSERT INTO autonomy_state(key,value_json,updated_at) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json,updated_at=excluded.updated_at",
            (str(key), json.dumps(value, ensure_ascii=False), ts),
        )
        self.conn.commit()
        return value

    def add_discovery(
        self, *, topic: str, title: str, summary: str, importance: int = 30,
        attention_level: str = "ambient", sources=None, metadata=None
    ):
        did = str(uuid4())
        level = attention_level if attention_level in {"ambient", "important", "critical"} else "ambient"
        importance = max(0, min(100, int(importance)))
        self.conn.execute(
            "INSERT INTO autonomy_discoveries(discovery_id,topic,title,summary,importance,attention_level,sources_json,created_at,metadata_json) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (
                did, str(topic)[:500], str(title)[:500], str(summary), importance, level,
                json.dumps(sources or [], ensure_ascii=False), now(),
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )
        self.conn.commit()
        return self.get_discovery(did)

    def get_discovery(self, discovery_id: str):
        row = self.conn.execute(
            "SELECT * FROM autonomy_discoveries WHERE discovery_id=?", (discovery_id,)
        ).fetchone()
        return self._discovery(row)

    def recent_discoveries(self, limit=20):
        rows = self.conn.execute(
            "SELECT * FROM autonomy_discoveries ORDER BY created_at DESC LIMIT ?", (int(limit),)
        ).fetchall()
        return [self._discovery(row) for row in rows]

    def recent_topics(self, limit=40):
        return [row["topic"] for row in self.conn.execute(
            "SELECT topic FROM autonomy_discoveries ORDER BY created_at DESC LIMIT ?", (int(limit),)
        ).fetchall()]

    def _discovery(self, row):
        if row is None:
            return None
        item = dict(row)
        item["sources"] = _loads(item.pop("sources_json", "[]"), [])
        item["metadata"] = _loads(item.pop("metadata_json", "{}"), {})
        return item

    @staticmethod
    def proposal_fingerprint(title: str, rationale: str = "") -> str:
        normalized = " ".join((str(title) + " " + str(rationale)).lower().split())[:1200]
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def add_proposal(
        self, *, title: str, summary: str, rationale: str, risk: str = "low",
        plan=None, metadata=None
    ):
        fingerprint = self.proposal_fingerprint(title, rationale)
        existing = self.conn.execute(
            "SELECT proposal_id FROM improvement_proposals WHERE fingerprint=?", (fingerprint,)
        ).fetchone()
        if existing:
            return self.get_proposal(existing["proposal_id"])
        pid = str(uuid4()); ts = now()
        risk = risk if risk in {"low", "medium", "high"} else "medium"
        self.conn.execute(
            "INSERT INTO improvement_proposals(proposal_id,title,summary,rationale,risk,status,plan_json,fingerprint,created_at,updated_at,metadata_json) "
            "VALUES(?,?,?,?,?,'pending',?,?,?,?,?)",
            (
                pid, str(title)[:500], str(summary), str(rationale), risk,
                json.dumps(plan or [], ensure_ascii=False), fingerprint, ts, ts,
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )
        self.conn.commit()
        return self.get_proposal(pid)

    def get_proposal(self, proposal_id: str):
        row = self.conn.execute(
            "SELECT * FROM improvement_proposals WHERE proposal_id=?", (proposal_id,)
        ).fetchone()
        return self._proposal(row)

    def proposals(self, status=None, limit=30):
        if status:
            rows = self.conn.execute(
                "SELECT * FROM improvement_proposals WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (str(status), int(limit)),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM improvement_proposals ORDER BY created_at DESC LIMIT ?", (int(limit),)
            ).fetchall()
        return [self._proposal(row) for row in rows]

    def set_proposal_status(self, proposal_id: str, status: str, metadata=None):
        allowed = {"pending", "approved", "rejected", "implementing", "prepared", "promoted", "rolled_back", "failed"}
        if status not in allowed:
            raise ValueError(status)
        current = self.get_proposal(proposal_id)
        if current is None:
            raise KeyError(proposal_id)
        merged = dict(current.get("metadata") or {})
        if metadata:
            merged.update(metadata)
        self.conn.execute(
            "UPDATE improvement_proposals SET status=?,updated_at=?,metadata_json=? WHERE proposal_id=?",
            (status, now(), json.dumps(merged, ensure_ascii=False), proposal_id),
        )
        self.conn.commit()
        return self.get_proposal(proposal_id)

    def _proposal(self, row):
        if row is None:
            return None
        item = dict(row)
        item["plan"] = _loads(item.pop("plan_json", "[]"), [])
        item["metadata"] = _loads(item.pop("metadata_json", "{}"), {})
        item.pop("fingerprint", None)
        return item

    def add_notification(
        self, *, kind: str, level: str, title: str, message: str = "",
        ref_type=None, ref_id=None, metadata=None, dedupe=True
    ):
        level = level if level in {"ambient", "important", "critical"} else "ambient"
        if dedupe:
            row = self.conn.execute(
                "SELECT notification_id FROM attention_notifications WHERE status='unread' AND kind=? AND title=? AND COALESCE(ref_id,'')=COALESCE(?, '') ORDER BY created_at DESC LIMIT 1",
                (kind, title, ref_id),
            ).fetchone()
            if row:
                return self.get_notification(row["notification_id"])
        nid = str(uuid4())
        self.conn.execute(
            "INSERT INTO attention_notifications(notification_id,kind,level,title,message,status,ref_type,ref_id,created_at,metadata_json) "
            "VALUES(?,?,?,?,?,'unread',?,?,?,?)",
            (
                nid, str(kind), level, str(title)[:500], str(message), ref_type, ref_id,
                now(), json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )
        self.conn.commit()
        return self.get_notification(nid)

    def get_notification(self, notification_id: str):
        row = self.conn.execute(
            "SELECT * FROM attention_notifications WHERE notification_id=?", (notification_id,)
        ).fetchone()
        return self._notification(row)

    def notifications(self, *, unread_only=True, limit=30):
        if unread_only:
            rows = self.conn.execute(
                "SELECT * FROM attention_notifications WHERE status='unread' "
                "ORDER BY CASE level WHEN 'critical' THEN 3 WHEN 'important' THEN 2 ELSE 1 END DESC, created_at DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM attention_notifications ORDER BY created_at DESC LIMIT ?", (int(limit),)
            ).fetchall()
        return [self._notification(row) for row in rows]

    def acknowledge_ref(self, ref_type: str, ref_id: str):
        ts = now()
        self.conn.execute(
            "UPDATE attention_notifications SET status='acknowledged',acknowledged_at=? "
            "WHERE status='unread' AND ref_type=? AND ref_id=?",
            (ts, str(ref_type), str(ref_id)),
        )
        self.conn.commit()

    def acknowledge(self, notification_id: str):
        self.conn.execute(
            "UPDATE attention_notifications SET status='acknowledged',acknowledged_at=? WHERE notification_id=?",
            (now(), notification_id),
        )
        self.conn.commit()
        return self.get_notification(notification_id)

    def _notification(self, row):
        if row is None:
            return None
        item = dict(row)
        item["metadata"] = _loads(item.pop("metadata_json", "{}"), {})
        return item

    def stats(self):
        def n(sql, params=()):
            row = self.conn.execute(sql, params).fetchone()
            return int(row["n"] if row else 0)
        return {
            "discoveries": n("SELECT COUNT(*) n FROM autonomy_discoveries"),
            "pending_improvements": n("SELECT COUNT(*) n FROM improvement_proposals WHERE status='pending'"),
            "approved_improvements": n("SELECT COUNT(*) n FROM improvement_proposals WHERE status IN ('approved','implementing','prepared')"),
            "unread_attention": n("SELECT COUNT(*) n FROM attention_notifications WHERE status='unread'"),
        }
