from __future__ import annotations

import time


class HealthService:
    def __init__(self, database, bus, tasks, run_id: str, started_monotonic: float) -> None:
        self.database = database
        self.bus = bus
        self.tasks = tasks
        self.run_id = run_id
        self.started_monotonic = started_monotonic
        self.last_recovery_count = 0

    def snapshot(self) -> dict:
        db_ok = self.database.health()
        bus_ok = not getattr(self.bus, "_closed", False)
        try:
            self.tasks.count()
            task_ok = True
        except Exception:
            task_ok = False
        components = [db_ok, bus_ok, task_ok]
        status = "healthy" if all(components) else ("degraded" if any(components) else "unhealthy")
        return {
            "status": status,
            "run_id": self.run_id,
            "uptime_seconds": round(time.monotonic() - self.started_monotonic, 3),
            "database": "healthy" if db_ok else "unhealthy",
            "event_bus": "healthy" if bus_ok else "unhealthy",
            "task_repository": "healthy" if task_ok else "unhealthy",
            "recovery": {"interrupted_found": self.last_recovery_count},
        }
