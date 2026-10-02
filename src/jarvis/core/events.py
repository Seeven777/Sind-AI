from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True, slots=True)
class Event:
    event_type: str
    severity: str = "info"
    payload: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=utc_now_iso)
    run_id: str | None = None
    task_id: str | None = None
    project_id: str | None = None
    agent_id: str | None = None
