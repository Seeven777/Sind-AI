import asyncio
from pathlib import Path
from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider

def test_default_workspace_and_briefing(tmp_path:Path):
    async def run():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider("Uma resposta longa o bastante para o teste do Jarvis Next funcionar normalmente."))
        try:
            assert rt.workspace["name"]=="Principal"
            b=rt.briefing.snapshot()
            assert b["schema"]=="jarvis.briefing.v2"
            assert b["connectors"]["counts"]["total"]==0
            assert len(b["connectors"]["sources"])==4
        finally: await rt.close()
    asyncio.run(run())
