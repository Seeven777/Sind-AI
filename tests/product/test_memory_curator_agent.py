import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_memory_curator_audits_without_deleting(tmp_path: Path):
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider())
        try:
            rt.memory.remember('Prefere interface simples.',memory_type='preference')
            rt.memory.remember('Prefere interface simples.',memory_type='preference')
            before=len(rt.memory.repository.recent(50))
            result=await rt.orchestrator.handle('Organize sua memória')
            after=len(rt.memory.repository.recent(50))
            assert result['agent']=='memory.curator'
            assert 'Grupos duplicados exatos: 1' in result['content']
            assert before==after
        finally:
            await rt.close()
    asyncio.run(scenario())
