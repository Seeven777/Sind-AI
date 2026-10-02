import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_hq_exposes_all_eight_operational_agents(tmp_path: Path):
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider())
        try:
            hq=rt.hq.snapshot()
            assert hq['schema']=='jarvis.hq.snapshot.v2'
            assert hq['metrics']['agents_total']==8
            assert hq['metrics']['agents_available']==8
            planned=[
                a for agents in hq['departments'].values() for a in agents
                if a['status']=='planned'
            ]
            assert planned==[]
        finally:
            await rt.close()
    asyncio.run(scenario())
