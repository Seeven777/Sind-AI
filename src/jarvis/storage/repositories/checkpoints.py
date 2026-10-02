from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CheckpointRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, task_id: str, sequence: int, state: dict, reason: str | None = None) -> dict:
        checkpoint_id = str(uuid4())
        created_at = now()
        self.connection.execute(
            """
            INSERT INTO task_checkpoints(
                checkpoint_id,task_id,sequence,created_at,state_json,reason
            ) VALUES(?,?,?,?,?,?)
            """,
            (
                checkpoint_id, task_id, sequence, created_at,
                json.dumps(state, ensure_ascii=False, separators=(",", ":")), reason,
            ),
        )
        self.connection.commit()
        return {
            "checkpoint_id": checkpoint_id,
            "task_id": task_id,
            "sequence": sequence,
            "created_at": created_at,
            "state": state,
            "reason": reason,
        }

    def latest(self, task_id: str) -> dict | None:
        row = self.connection.execute(
            """
            SELECT * FROM task_checkpoints
            WHERE task_id=?
            ORDER BY sequence DESC
            LIMIT 1
            """,
            (task_id,),
        ).fetchone()
        if row is None:
            return None
        return {
            "checkpoint_id": row["checkpoint_id"],
            "task_id": row["task_id"],
            "sequence": int(row["sequence"]),
            "created_at": row["created_at"],
            "state": json.loads(row["state_json"]),
            "reason": row["reason"],
        }
