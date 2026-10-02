import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_developer_is_real_agent_and_persists_artifact(tmp_path: Path):
    async def scenario():
        provider=MockModelProvider(
            "# Implementação\n\nDiagnóstico completo, solução proposta, código de exemplo, testes e riscos técnicos suficientes."
        )
        rt=await start_product_runtime(tmp_path,model_provider=provider)
        try:
            result=await rt.orchestrator.handle('Implemente um script Python para validar arquivos JSON.')
            assert result['agent']=='engineering.developer'
            assert result['artifact_id']
            assert Path(result['artifact_path']).exists()
        finally:
            await rt.close()
    asyncio.run(scenario())
