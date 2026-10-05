import asyncio
from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_capability_inventory_knows_agents_tools_connectors(tmp_path):
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider())
        try:
            r=rt.capabilities.resolve("coding")
            assert r["status"]=="available"
            assert any(x["id"]=="engineering.developer" for x in r["matches"])
            web=rt.capabilities.resolve("web.search")
            assert web["status"]=="available"
            inv=rt.capabilities.inventory()
            assert len(inv["agents"])==8
            assert len(inv["specialists"])>=0
            assert all(not x["id"].startswith("agency.") for x in inv["agents"])
            assert "web.search" in inv["tools"]
        finally:
            await rt.close()
    asyncio.run(scenario())
