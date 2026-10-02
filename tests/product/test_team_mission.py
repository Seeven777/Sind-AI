import asyncio
from pathlib import Path
from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider
from jarvis.tasks import TaskStatus

class SequenceProvider(MockModelProvider):
    def __init__(self):
        super().__init__("unused")
        self.calls=0
    def chat(self,messages,*,model=None,system=None):
        self.calls+=1
        texts={
            1:"# Pesquisa\n\nEvidências, riscos e perguntas suficientemente detalhadas para a missão.",
            2:"# Análise\n\nPrioridades, riscos, decisões e lacunas suficientemente detalhadas para a missão.",
            3:"# Entrega\n\nPlano concreto, etapas e resultado final suficientemente detalhado para uso.",
            4:"# Revisão\n\nA entrega atende ao objetivo e mantém as incertezas explícitas.\n\nVERDICT: PASS",
        }
        from jarvis.models.base import ModelResponse
        return ModelResponse(texts[self.calls],model or "mock-model","mock")

def test_team_mission_runs_four_agents(tmp_path:Path):
    async def run():
        provider=SequenceProvider()
        rt=await start_product_runtime(tmp_path,model_provider=provider)
        try:
            result=await rt.missions.run("Crie um projeto completo.")
            assert result["kind"]=="team_mission"
            assert result["agents"]==["creative.creator","review.verifier"]
            assert provider.calls==2
            assert Path(result["artifact_path"]).exists()
            assert rt.foundation.tasks.get(result["task_id"]).status==TaskStatus.COMPLETED
            snap=rt.hq.snapshot()
            mission=next(m for m in snap["missions"] if m["mission_id"]==result["mission_id"])
            assert [s["status"] for s in mission["steps"]]==["completed"]*2
        finally: await rt.close()
    asyncio.run(run())
