import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_local_only_removes_external_capabilities(tmp_path:Path,monkeypatch):
    monkeypatch.setenv("JARVIS_LOCAL_ONLY","1")
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider())
        try:
            tools=set(rt.tool_registry.list_ids())
            assert "web.search" not in tools
            assert "browser.open" not in tools
            assert "whatsapp.send_message" not in tools
            assert "files.read_text" in tools
            assert set(rt.connectors.health())=={"local.inbox","local.calendar"}
            assert rt.foundation.config.local_only is True
        finally:
            await rt.close()
    asyncio.run(scenario())
