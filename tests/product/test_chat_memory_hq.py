import asyncio
from pathlib import Path
from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider
def test_chat_memory_hq(tmp_path:Path):
 async def run():
  rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider('Resposta útil e suficientemente longa para o teste do Jarvis.'))
  try:
   cid=rt.chat.new_conversation(); result=await rt.chat.send(cid,'Olá Jarvis'); assert result['kind']=='chat'; assert len(rt.foundation.database.conn().execute('SELECT * FROM messages WHERE conversation_id=?',(cid,)).fetchall())==2; rt.memory.remember('O usuário prefere interfaces simples.',memory_type='preference'); assert rt.memory.context('interfaces'); snap=rt.hq.snapshot(); assert snap['core']['name']=='Jarvis'; assert any(a['id']=='research.general' and a['available'] for arr in snap['departments'].values() for a in arr); assert all(a['available'] for arr in snap['departments'].values() for a in arr)
  finally: await rt.close()
 asyncio.run(run())
