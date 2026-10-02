import asyncio
import sqlite3
from pathlib import Path

import pytest

from jarvis.core.errors import StateTransitionError
from jarvis.core.event_bus import EventBus
from jarvis.storage import Database, MigrationEngine
from jarvis.storage.repositories import CheckpointRepository, TaskRepository
from jarvis.tasks import TaskStatus
from jarvis.tasks.service import TaskService


def test_invalid_transition(tmp_path: Path):
    async def scenario():
        db = Database(tmp_path / "x.db")
        conn = db.open()
        MigrationEngine(conn, Path(__file__).resolve().parents[2] / "migrations").apply_pending()
        bus = EventBus()
        service = TaskService(TaskRepository(conn), CheckpointRepository(conn), bus, "run")
        task = await service.create("x", "y")
        with pytest.raises(StateTransitionError):
            await service.transition(task.task_id, TaskStatus.COMPLETED)
        db.close()

    asyncio.run(scenario())
