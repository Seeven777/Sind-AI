from __future__ import annotations

import logging
import time
from uuid import uuid4
from dataclasses import dataclass
from pathlib import Path

from jarvis import __version__
from jarvis.config import ensure_default_config, load_config
from jarvis.core.event_bus import EventBus
from jarvis.core.events import Event
from jarvis.storage import Database, MigrationEngine
from jarvis.storage.repositories import (
    CheckpointRepository,
    EventRepository,
    RunRepository,
    TaskRepository,
)
from jarvis.tasks.recovery import RecoveryService
from jarvis.tasks.service import TaskService
from .health import HealthService
from .instance_lock import InstanceLock
from .logging_setup import configure_logging


@dataclass(slots=True)
class Runtime:
    config: object
    database: Database
    bus: EventBus
    run_id: str
    lock: InstanceLock
    events: EventRepository
    tasks: TaskRepository
    checkpoints: CheckpointRepository
    runs: RunRepository
    task_service: TaskService
    recovery: RecoveryService
    health: HealthService
    _persistence_subscription: object | None = None
    _closed: bool = False

    async def close(self) -> None:
        if self._closed:
            return
        try:
            await self.bus.publish(Event("system.shutdown", run_id=self.run_id))
            await self.bus.close()
            self.runs.mark_clean(self.run_id)
        finally:
            self.database.close()
            self.lock.release()
            self._closed = True


def _project_root() -> Path:
    # src/jarvis/app/bootstrap.py -> repository root
    return Path(__file__).resolve().parents[3]


async def start_runtime(data_dir: Path | None = None) -> Runtime:
    config = load_config(data_dir)
    config.data_dir.mkdir(parents=True, exist_ok=True)
    ensure_default_config(config)
    configure_logging(config.log_path, config.logging.level)
    log = logging.getLogger("jarvis.bootstrap")

    # Lock comes before opening/mutating the database. A competing instance
    # must not create a fake unclean system_run.
    run_id = str(uuid4())
    lock = InstanceLock(config.data_dir / "runtime" / "instance.lock")
    db = Database(config.database_path)
    try:
        if config.runtime.single_instance:
            lock.acquire(run_id)

        conn = db.open()
        migrations_dir = _project_root() / "migrations"
        MigrationEngine(conn, migrations_dir).apply_pending()

        runs = RunRepository(conn)
        runs.start(
            __version__,
            {"environment": config.system.environment},
            run_id=run_id,
        )

        bus = EventBus()
        events = EventRepository(conn)
        tasks = TaskRepository(conn)
        checkpoints = CheckpointRepository(conn)

        async def persist_event(event: Event) -> None:
            events.append(event)

        persistence_sub = await bus.subscribe("*", persist_event)

        task_service = TaskService(tasks, checkpoints, bus, run_id)
        recovery = RecoveryService(tasks, checkpoints, bus, run_id)
        health = HealthService(db, bus, tasks, run_id, time.monotonic())

        runtime = Runtime(
            config=config,
            database=db,
            bus=bus,
            run_id=run_id,
            lock=lock,
            events=events,
            tasks=tasks,
            checkpoints=checkpoints,
            runs=runs,
            task_service=task_service,
            recovery=recovery,
            health=health,
            _persistence_subscription=persistence_sub,
        )

        unclean = runs.unclean_runs(exclude_run_id=run_id)
        recovered = []
        if unclean:
            recovered = await recovery.recover_interrupted()
        health.last_recovery_count = len(recovered)

        await bus.publish(Event(
            "system.started",
            run_id=run_id,
            payload={"unclean_runs_detected": len(unclean)},
        ))
        await bus.publish(Event(
            "system.ready",
            run_id=run_id,
            payload={"status": health.snapshot()["status"]},
        ))
        log.info("Jarvis foundation ready", extra={"run_id": run_id, "event": "system.ready"})
        return runtime
    except Exception:
        db.close()
        lock.release()
        raise
