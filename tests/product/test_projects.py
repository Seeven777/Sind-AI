import asyncio
from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_project_repository_roundtrip(tmp_path):
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider())
        try:
            p=rt.projects.create("Projeto A","Objetivo",rt.workspace["workspace_id"])
            assert p["name"]=="Projeto A"
            p2=rt.projects.update(p["project_id"],status="paused")
            assert p2["status"]=="paused"
            assert rt.projects.list()[0]["project_id"]==p["project_id"]
        finally:
            await rt.close()
    asyncio.run(scenario())
