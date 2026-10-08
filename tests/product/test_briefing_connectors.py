import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_briefing_uses_connector_data(tmp_path:Path):
    async def scenario():
        data=tmp_path/'data'
        inbox=data/'connectors'/'inbox'
        inbox.mkdir(parents=True)
        (inbox/'Prazo.txt').write_text('urgente: prazo hoje',encoding='utf-8')
        rt=await start_product_runtime(data,model_provider=MockModelProvider())
        try:
            snap=rt.briefing.snapshot()
            assert snap['summary']['inbox_unread']==1
            assert snap['summary']['connector_sources']==5
            assert any(x['kind']=='inbox' for x in snap['priorities'])
            result=await rt.orchestrator.handle('Me dê meu briefing do dia')
            assert result['kind']=='briefing'
            assert 'Caixa de entrada não lida: 1' in result['content']
        finally:
            await rt.close()
    asyncio.run(scenario())
