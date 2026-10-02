from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from jarvis.tasks.models import Task, TaskStatus


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_to_task(row: sqlite3.Row) -> Task:
    return Task(
        task_id=row["task_id"],
        title=row["title"],
        objective=row["objective"],
        status=TaskStatus(row["status"]),
        priority=int(row["priority"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        checkpoint_seq=int(row["checkpoint_seq"]),
        metadata=json.loads(row["metadata_json"] or "{}"),
        last_error=row["last_error"],
    )


class TaskRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def create(self, title: str, objective: str, priority: int = 50, metadata: dict | None = None) -> Task:
        task_id = str(uuid4())
        ts = now()
        self.connection.execute(
            """
            INSERT INTO tasks(
                task_id,title,objective,status,priority,created_at,updated_at,metadata_json
            ) VALUES(?,?,?,?,?,?,?,?)
            """,
            (
                task_id, title, objective, TaskStatus.CREATED.value, priority, ts, ts,
                json.dumps(metadata or {}, ensure_ascii=False, separators=(",", ":")),
            ),
        )
        self.connection.commit()
        return self.get(task_id)

    def get(self, task_id: str) -> Task:
        row = self.connection.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
        if row is None:
            raise KeyError(task_id)
        return row_to_task(row)

    def set_status(self, task_id: str, status: TaskStatus, *, last_error: str | None = None) -> Task:
        current = self.get(task_id)
        ts = now()
        started_at = current.started_at
        completed_at = current.completed_at
        if status == TaskStatus.RUNNING and started_at is None:
            started_at = ts
        if status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
            completed_at = ts
        self.connection.execute(
            """
            UPDATE tasks
            SET status=?,updated_at=?,started_at=?,completed_at=?,last_error=?
            WHERE task_id=?
            """,
            (status.value, ts, started_at, completed_at, last_error, task_id),
        )
        self.connection.commit()
        return self.get(task_id)

    def set_checkpoint_seq(self, task_id: str, sequence: int) -> Task:
        self.connection.execute(
            "UPDATE tasks SET checkpoint_seq=?,updated_at=? WHERE task_id=?",
            (sequence, now(), task_id),
        )
        self.connection.commit()
        return self.get(task_id)

    def list_by_status(self, statuses: set[TaskStatus]) -> list[Task]:
        if not statuses:
            return []
        values = [s.value for s in statuses]
        placeholders = ",".join("?" for _ in values)
        rows = self.connection.execute(
            f"SELECT * FROM tasks WHERE status IN ({placeholders}) ORDER BY priority DESC,created_at",
            values,
        ).fetchall()
        return [row_to_task(r) for r in rows]

    def count(self) -> int:
        row = self.connection.execute("SELECT COUNT(*) AS n FROM tasks").fetchone()
        return int(row["n"])
