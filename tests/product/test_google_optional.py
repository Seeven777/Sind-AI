import asyncio
from pathlib import Path
from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_google_connectors_are_safe_when_unconfigured(tmp_path:Path):
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider())
        try:
            health=rt.connectors.health()
            assert health["google.gmail"]["status"]=="unconfigured"
            assert health["google.calendar"]["status"]=="unconfigured"
            result=await rt.connectors.sync_all()
            google=[x for x in result if x["connector_id"].startswith("google.")]
            assert all(x["status"]=="skipped" for x in google)
        finally:
            await rt.close()
    asyncio.run(scenario())
