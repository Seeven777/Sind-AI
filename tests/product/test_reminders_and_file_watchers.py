import asyncio
from datetime import datetime,timezone,timedelta

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_one_time_reminder_and_file_watcher(tmp_path):
    async def scenario():
        rt=await start_product_runtime(tmp_path/"data",model_provider=MockModelProvider())
        try:
            run_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
            job=rt.scheduler_repository.create_once("R","reminder",run_at,{"message":"teste"})
            results=await rt.scheduler.run_due()
            assert any(x["job_id"]==job and x["status"]=="completed" for x in results)

            target=tmp_path/"watched.txt"
            target.write_text("a",encoding="utf-8")
            wid=rt.watcher_repository.ensure("Arquivo teste","file.changed",{"path":str(target)})
            first=await rt.watchers.check_all()
            file_first=[x for x in first if x["watcher_id"]==wid][0]
            assert file_first["triggered"] is False
            target.write_text("b",encoding="utf-8")
            second=await rt.watchers.check_all()
            file_second=[x for x in second if x["watcher_id"]==wid][0]
            assert file_second["triggered"] is True
        finally:
            await rt.close()
    asyncio.run(scenario())
