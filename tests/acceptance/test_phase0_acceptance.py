import asyncio
from pathlib import Path

from jarvis.app.bootstrap import start_runtime
from jarvis.tasks import TaskStatus


def test_phase0_acceptance(tmp_path: Path):
    async def scenario():
        # Boot 1
        rt1 = await start_runtime(tmp_path)
        task = await rt1.task_service.create("Acceptance", "Foundation")
        await rt1.task_service.transition(task.task_id, TaskStatus.PLANNING)
        await rt1.task_service.transition(task.task_id, TaskStatus.READY)
        await rt1.task_service.transition(task.task_id, TaskStatus.RUNNING)
        await rt1.task_service.checkpoint(task.task_id, {"step": 1})
        await rt1.task_service.checkpoint(task.task_id, {"step": 2})

        # Crash simulation.
        rt1.database.close()
        rt1.lock.release()

        # Boot 2 recovers.
        rt2 = await start_runtime(tmp_path)
        assert rt2.tasks.get(task.task_id).status == TaskStatus.INTERRUPTED
        assert rt2.checkpoints.latest(task.task_id)["sequence"] == 2
        await rt2.task_service.transition(task.task_id, TaskStatus.RUNNING)
        await rt2.task_service.transition(task.task_id, TaskStatus.VERIFYING)
        await rt2.task_service.transition(task.task_id, TaskStatus.COMPLETED)
        await rt2.close()

        # Boot 3 is clean, no false recovery.
        rt3 = await start_runtime(tmp_path)
        try:
            assert rt3.health.last_recovery_count == 0
            assert rt3.health.snapshot()["status"] == "healthy"
            assert rt3.tasks.get(task.task_id).status == TaskStatus.COMPLETED
        finally:
            await rt3.close()

    asyncio.run(scenario())
