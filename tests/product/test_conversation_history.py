import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models.mock import MockModelProvider


def test_conversation_history_persists_and_is_searchable(tmp_path):
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider())
        try:
            cid=rt.chat.new_conversation('Teste')
            await rt.chat.send(cid,'Olá Jarvis')
            rows=rt.chat.list_conversations(search='Olá')
            assert rows and rows[0]['conversation_id']==cid
            convo=rt.chat.get_conversation(cid)
            assert [m['role'] for m in convo['messages']][-2:]==['user','assistant']
            rt.chat.rename_conversation(cid,'Conversa renomeada')
            updated=rt.chat.get_conversation(cid)
            assert updated['title']=='Conversa renomeada'
            rt.chat.set_conversation_flags(cid,pinned=True)
            assert rt.chat.get_conversation(cid)['pinned'] is True
            regenerated=await rt.chat.regenerate(cid)
            assert regenerated['content']
            assert rt.chat.get_conversation(cid)['messages'][-1]['metadata']['regenerated'] is True
            rt.chat.set_conversation_flags(cid,archived=True)
            assert rt.chat.list_conversations(search='Teste') == []
        finally:
            await rt.close()
    asyncio.run(scenario())


def test_new_ui_files_present():
    root=Path(__file__).resolve().parents[2]
    assert (root/'src/jarvis/ui/hq_web/office3d.js').is_file()
    assert (root/'src/jarvis/ui/hq_web/office3d.css').is_file()
    assert 'three@0.186.1' in (root/'src/jarvis/ui/hq_web/index.html').read_text(encoding='utf-8')
