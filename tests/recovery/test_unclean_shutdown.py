import asyncio
from pathlib import Path

from jarvis.app.bootstrap import start_runtime
from jarvis.tasks import TaskStatus


def test_unclean_previous_run_marks_running_task_interrupted(tmp_path: Path):
    async def scenario():
        rt1 = await start_runtime(tmp_path)
        task = await rt1.task_service.create("Crash", "Recover")
        await rt1.task_service.transition(task.task_id, TaskStatus.READY)
        await rt1.task_service.transition(task.task_id, TaskStatus.RUNNING)
        await rt1.task_service.checkpoint(task.task_id, {"step": "safe"})

        # Simulated crash: database closes and lock disappears, but run remains unclean.
        rt1.database.close()
        rt1.lock.release()

        rt2 = await start_runtime(tmp_path)
        try:
            recovered = rt2.tasks.get(task.task_id)
            assert recovered.status == TaskStatus.INTERRUPTED
            assert rt2.health.last_recovery_count == 1
            assert rt2.checkpoints.latest(task.task_id)["state"]["step"] == "safe"
        finally:
            await rt2.close()

    asyncio.run(scenario())
