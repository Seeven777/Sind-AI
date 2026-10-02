from __future__ import annotations

import json
import sqlite3
from jarvis.core.events import Event


class EventRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def append(self, event: Event) -> None:
        self.connection.execute(
            """
            INSERT INTO events(
                event_id,event_type,timestamp,run_id,task_id,project_id,
                agent_id,severity,payload_json
            ) VALUES(?,?,?,?,?,?,?,?,?)
            """,
            (
                event.event_id, event.event_type, event.timestamp, event.run_id,
                event.task_id, event.project_id, event.agent_id, event.severity,
                json.dumps(event.payload, ensure_ascii=False, separators=(",", ":")),
            ),
        )
        self.connection.commit()

    def by_task(self, task_id: str) -> list[sqlite3.Row]:
        return self.connection.execute(
            "SELECT * FROM events WHERE task_id=? ORDER BY timestamp,event_id",
            (task_id,),
        ).fetchall()

    def count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS n FROM events").fetchone()
        return int(row["n"])
