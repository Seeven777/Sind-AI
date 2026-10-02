import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_hq_projection_has_office_contract(tmp_path: Path):
    async def scenario():
        rt = await start_product_runtime(
            tmp_path,
            model_provider=MockModelProvider(
                "Relatório de pesquisa suficientemente detalhado para validar a missão e o artifact persistente."
            ),
        )
        try:
            before = rt.hq.snapshot()
            assert before["schema"] == "jarvis.hq.snapshot.v2"
            assert "Research" in before["departments"]
            research = next(a for a in before["departments"]["Research"] if a["id"] == "research.general")
            assert research["available"] is True
            assert research["status"] == "idle"

            result = await rt.orchestrator.handle("Pesquise a arquitetura do Jarvis HQ.")
            after = rt.hq.snapshot()
            research = next(a for a in after["departments"]["Research"] if a["id"] == "research.general")
            assert result["kind"] == "delegated"
            assert research["last_status"] == "completed"
            assert any(event["type"] == "agent.completed" for event in after["timeline"])
        finally:
            await rt.close()
    asyncio.run(scenario())
