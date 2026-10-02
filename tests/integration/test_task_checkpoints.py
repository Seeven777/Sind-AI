import asyncio
from pathlib import Path

from jarvis.app.bootstrap import start_runtime
from jarvis.tasks import TaskStatus


def test_checkpoints_increment_and_latest(tmp_path: Path):
    async def scenario():
        rt = await start_runtime(tmp_path)
        try:
            task = await rt.task_service.create("Demo", "Checkpoint")
            await rt.task_service.transition(task.task_id, TaskStatus.READY)
            await rt.task_service.transition(task.task_id, TaskStatus.RUNNING)
            await rt.task_service.checkpoint(task.task_id, {"step": 1})
            await rt.task_service.checkpoint(task.task_id, {"step": 2})
            latest = rt.checkpoints.latest(task.task_id)
            assert latest["sequence"] == 2
            assert latest["state"]["step"] == 2
        finally:
            await rt.close()

    asyncio.run(scenario())
