from __future__ import annotations

from jarvis.core.errors import StateTransitionError
from jarvis.core.event_bus import EventBus
from jarvis.core.events import Event
from jarvis.storage.repositories.checkpoints import CheckpointRepository
from jarvis.storage.repositories.tasks import TaskRepository
from .models import ALLOWED_TRANSITIONS, Task, TaskStatus


class TaskService:
    def __init__(
        self,
        tasks: TaskRepository,
        checkpoints: CheckpointRepository,
        bus: EventBus,
        run_id: str,
    ) -> None:
        self.tasks = tasks
        self.checkpoints = checkpoints
        self.bus = bus
        self.run_id = run_id

    async def create(self, title: str, objective: str, priority: int = 50, metadata: dict | None = None) -> Task:
        task = self.tasks.create(title, objective, priority, metadata)
        await self.bus.publish(Event(
            "task.created", run_id=self.run_id, task_id=task.task_id,
            payload={"title": task.title, "priority": task.priority},
        ))
        return task

    async def transition(self, task_id: str, target: TaskStatus, *, error: str | None = None) -> Task:
        current = self.tasks.get(task_id)
        if target not in ALLOWED_TRANSITIONS[current.status]:
            raise StateTransitionError(f"Invalid transition: {current.status.value} -> {target.value}")
        task = self.tasks.set_status(task_id, target, last_error=error)
        await self.bus.publish(Event(
            f"task.{target.value}",
            severity="error" if target == TaskStatus.FAILED else "info",
            run_id=self.run_id,
            task_id=task.task_id,
            payload={"from": current.status.value, "to": target.value, "error": error},
        ))
        return task

    async def checkpoint(self, task_id: str, state: dict, reason: str | None = None) -> dict:
        task = self.tasks.get(task_id)
        seq = task.checkpoint_seq + 1
        cp = self.checkpoints.create(task_id, seq, state, reason)
        self.tasks.set_checkpoint_seq(task_id, seq)
        await self.bus.publish(Event(
            "task.checkpoint", run_id=self.run_id, task_id=task_id,
            payload={"sequence": seq, "reason": reason},
        ))
        return cp
