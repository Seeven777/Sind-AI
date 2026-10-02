from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class TaskStatus(StrEnum):
    CREATED = "created"
    PLANNING = "planning"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    BLOCKED = "blocked"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    INTERRUPTED = "interrupted"


TERMINAL_STATES = {
    TaskStatus.COMPLETED,
    TaskStatus.FAILED,
    TaskStatus.CANCELLED,
}

ALLOWED_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.CREATED: {TaskStatus.PLANNING, TaskStatus.READY, TaskStatus.CANCELLED},
    TaskStatus.PLANNING: {TaskStatus.READY, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.INTERRUPTED},
    TaskStatus.READY: {TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.RUNNING: {
        TaskStatus.PAUSED, TaskStatus.BLOCKED, TaskStatus.VERIFYING,
        TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.INTERRUPTED,
    },
    TaskStatus.PAUSED: {TaskStatus.READY, TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.BLOCKED: {TaskStatus.READY, TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.VERIFYING: {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.INTERRUPTED},
    TaskStatus.INTERRUPTED: {TaskStatus.READY, TaskStatus.RUNNING, TaskStatus.FAILED, TaskStatus.CANCELLED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: set(),
    TaskStatus.CANCELLED: set(),
}


@dataclass(slots=True)
class Task:
    task_id: str
    title: str
    objective: str
    status: TaskStatus
    priority: int
    created_at: str
    updated_at: str
    started_at: str | None = None
    completed_at: str | None = None
    checkpoint_seq: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    last_error: str | None = None
