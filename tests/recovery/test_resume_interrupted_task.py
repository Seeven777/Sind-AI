import asyncio
from pathlib import Path

from jarvis.app.bootstrap import start_runtime
from jarvis.tasks import TaskStatus


def test_interrupted_task_can_return_to_ready(tmp_path: Path):
    async def scenario():
        rt1 = await start_runtime(tmp_path)
        task = await rt1.task_service.create("Resume", "Test")
        await rt1.task_service.transition(task.task_id, TaskStatus.READY)
        await rt1.task_service.transition(task.task_id, TaskStatus.RUNNING)
        await rt1.task_service.checkpoint(task.task_id, {"progress": 50})
        rt1.database.close()
        rt1.lock.release()

        rt2 = await start_runtime(tmp_path)
        try:
            assert rt2.tasks.get(task.task_id).status == TaskStatus.INTERRUPTED
            resumed = await rt2.task_service.transition(task.task_id, TaskStatus.READY)
            assert resumed.status == TaskStatus.READY
        finally:
            await rt2.close()

    asyncio.run(scenario())
