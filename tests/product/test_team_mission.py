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
            2:"# Revisão\n\nA entrega atende ao objetivo e mantém as incertezas explícitas.\n\nVERDICT: PASS",
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


def test_team_mission_fails_when_reviewer_requests_revision(tmp_path: Path):
    class RevisingProvider(MockModelProvider):
        def __init__(self):
            super().__init__("unused")
            self.calls = 0

        def chat(self, messages, *, model=None, system=None):
            self.calls += 1
            from jarvis.models.base import ModelResponse
            content = (
                "# Entrega\n\nUma proposta que precisa de revisão."
                if self.calls == 1
                else "# Revisão\n\nA entrega possui uma falha material.\n\nVERDICT: REVISE"
            )
            return ModelResponse(content, model or "mock-model", "mock")

    async def run():
        rt = await start_product_runtime(tmp_path, model_provider=RevisingProvider())
        try:
            result = await rt.missions.run("Crie uma entrega que será revisada.")
            assert result["kind"] == "team_mission_review_failed"
            assert result["review_passed"] is False
            assert rt.foundation.tasks.get(result["task_id"]).status == TaskStatus.FAILED
            mission = next(
                mission for mission in rt.hq.snapshot()["missions"]
                if mission["mission_id"] == result["mission_id"]
            )
            assert mission["status"] == "failed"
        finally:
            await rt.close()

    asyncio.run(run())
