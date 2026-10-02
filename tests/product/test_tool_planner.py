import asyncio
import json

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_generic_tool_plan_executes_safe_read(tmp_path):
    response=json.dumps({
        "tool_id":"system.time",
        "payload":{},
        "reason":"pedido de hora real",
    })
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider(response))
        try:
            result=await rt.orchestrator.handle("Faça no computador uma consulta do relógio do sistema")
            assert result["kind"]=="operator"
            assert result["metadata"]["status"]=="completed"
            assert result["metadata"]["plan"]["tool_id"]=="system.time"
        finally:
            await rt.close()
    asyncio.run(scenario())
