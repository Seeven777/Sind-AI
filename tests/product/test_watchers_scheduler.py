import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_priority_watcher_triggers_once_for_new_important_item(tmp_path:Path):
    async def scenario():
        data=tmp_path/'data'
        inbox=data/'connectors'/'inbox'
        inbox.mkdir(parents=True)
        rt=await start_product_runtime(data,model_provider=MockModelProvider())
        try:
            # Item arrives after startup, then an explicit sync observes it.
            (inbox/'urgente.txt').write_text('URGENTE: prazo de hoje',encoding='utf-8')
            await rt.connectors.sync_all()
            first=await rt.watchers.check_all()
            priority=[x for x in first if x['kind']=='connector.priority'][0]
            assert priority['triggered'] is True
            second=await rt.watchers.check_all()
            priority2=[x for x in second if x['kind']=='connector.priority'][0]
            assert priority2['triggered'] is False
        finally:
            await rt.close()
    asyncio.run(scenario())


def test_scheduler_has_durable_default_jobs(tmp_path:Path):
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider())
        try:
            jobs=rt.scheduler_repository.all()
            kinds={x['kind'] for x in jobs}
            assert {'connector.sync_all','watchers.check'} <= kinds
            # Force jobs due and execute a deterministic scheduler tick.
            rt.foundation.database.conn().execute(
                "UPDATE scheduled_jobs SET next_run_at='2000-01-01T00:00:00+00:00'"
            )
            rt.foundation.database.conn().commit()
            result=await rt.scheduler.run_due()
            assert len(result)==2
            assert all(x['status']=='completed' for x in result)
        finally:
            await rt.close()
    asyncio.run(scenario())
