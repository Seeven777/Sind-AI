import asyncio
from pathlib import Path
from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider

def test_hq_v2_has_four_active_specialists(tmp_path:Path):
    async def run():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider("Conteúdo suficientemente longo para passar pelos testes do agente e artifact."))
        try:
            snap=rt.hq.snapshot()
            assert snap["schema"]=="jarvis.hq.snapshot.v2"
            active=[a for arr in snap["departments"].values() for a in arr if a["available"]]
            ids={a["id"] for a in active}
            assert {"research.general","intelligence.analyst","creative.creator","review.verifier"} <= ids
        finally: await rt.close()
    asyncio.run(run())
