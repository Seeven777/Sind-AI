from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RunRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def start(self, version: str, metadata: dict | None = None, run_id: str | None = None) -> str:
        run_id = run_id or str(uuid4())
        self.connection.execute(
            """
            INSERT INTO system_runs(
                run_id,started_at,shutdown_clean,version,pid,metadata_json
            ) VALUES(?,?,0,?,?,?)
            """,
            (
                run_id, now(), version, os.getpid(),
                json.dumps(metadata or {}, ensure_ascii=False, separators=(",", ":")),
            ),
        )
        self.connection.commit()
        return run_id

    def mark_clean(self, run_id: str) -> None:
        self.connection.execute(
            "UPDATE system_runs SET stopped_at=?,shutdown_clean=1 WHERE run_id=?",
            (now(), run_id),
        )
        self.connection.commit()

    def unclean_runs(self, *, exclude_run_id: str | None = None) -> list[sqlite3.Row]:
        if exclude_run_id:
            return self.connection.execute(
                "SELECT * FROM system_runs WHERE shutdown_clean=0 AND run_id<>? ORDER BY started_at",
                (exclude_run_id,),
            ).fetchall()
        return self.connection.execute(
            "SELECT * FROM system_runs WHERE shutdown_clean=0 ORDER BY started_at"
        ).fetchall()
