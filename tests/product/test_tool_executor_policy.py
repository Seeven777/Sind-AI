import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_tool_executor_does_not_write_before_approval(tmp_path: Path):
    async def scenario():
        rt=await start_product_runtime(tmp_path/'data',model_provider=MockModelProvider())
        try:
            result=await rt.tool_executor.execute(
                'files.write_workspace_text',
                {'relative_path':'pending.txt','content':'x'}
            )
            assert result.status=='approval_required'
            assert not (rt.foundation.config.data_dir/'workspace_files'/'pending.txt').exists()
        finally:
            await rt.close()
    asyncio.run(scenario())
