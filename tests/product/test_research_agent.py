import asyncio
from pathlib import Path
from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider
from jarvis.tasks import TaskStatus
def test_delegates_and_persists_artifact(tmp_path:Path):
 async def run():
  rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider('# Relatório\n\nPerguntas, hipóteses, evidências desejáveis, riscos e próximos passos para {{PROMPT}}.'))
  try:
   result=await rt.orchestrator.handle('Pesquise como estruturar um sistema de agentes verificáveis.'); assert result['kind']=='delegated'; assert result['agent']=='research.general'; assert Path(result['artifact_path']).exists(); assert rt.foundation.tasks.get(result['task_id']).status==TaskStatus.COMPLETED
  finally: await rt.close()
 asyncio.run(run())
