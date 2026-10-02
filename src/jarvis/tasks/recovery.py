from __future__ import annotations

from jarvis.core.event_bus import EventBus
from jarvis.core.events import Event
from jarvis.storage.repositories.checkpoints import CheckpointRepository
from jarvis.storage.repositories.tasks import TaskRepository
from .models import TaskStatus

_RECOVERY_STATES = {
    TaskStatus.PLANNING,
    TaskStatus.RUNNING,
    TaskStatus.VERIFYING,
}


class RecoveryService:
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

    async def recover_interrupted(self) -> list[dict]:
        recovered: list[dict] = []
        for task in self.tasks.list_by_status(_RECOVERY_STATES):
            previous = task.status
            updated = self.tasks.set_status(task.task_id, TaskStatus.INTERRUPTED)
            checkpoint = self.checkpoints.latest(task.task_id)
            payload = {
                "previous_status": previous.value,
                "checkpoint_sequence": checkpoint["sequence"] if checkpoint else None,
                "resumable": checkpoint is not None,
            }
            await self.bus.publish(Event(
                "task.interrupted",
                severity="warning",
                run_id=self.run_id,
                task_id=task.task_id,
                payload=payload,
            ))
            recovered.append({
                "task": updated,
                "checkpoint": checkpoint,
                "resumable": checkpoint is not None,
            })
        return recovered
