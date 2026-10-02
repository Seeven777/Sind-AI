import asyncio
from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_optional_computer_layers_never_break_startup(tmp_path):
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider())
        try:
            assert rt.browser.health()["status"] in {"healthy","unavailable"}
            assert rt.windows.health()["status"] in {"healthy","unavailable"}
            voice=rt.voice.health()
            assert voice["stt"]["status"] in {"healthy","unconfigured"}
            assert voice["tts"]["status"] in {"healthy","unconfigured"}
        finally:
            await rt.close()
    asyncio.run(scenario())
