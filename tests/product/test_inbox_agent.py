import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_inbox_agent_triages_connector_items(tmp_path:Path):
    async def scenario():
        data=tmp_path/'data'
        inbox=data/'connectors'/'inbox'
        inbox.mkdir(parents=True)
        (inbox/'Importante.txt').write_text('URGENTE: aprovar material hoje.',encoding='utf-8')
        rt=await start_product_runtime(data,model_provider=MockModelProvider())
        try:
            result=await rt.orchestrator.handle('Resuma minha caixa de entrada')
            assert result['agent']=='administration.inbox'
            assert 'Itens não lidos: 1' in result['content']
            assert '[ALTA] Importante' in result['content']
            assert Path(result['artifact_path']).exists()
        finally:
            await rt.close()
    asyncio.run(scenario())
