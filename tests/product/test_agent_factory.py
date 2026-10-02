import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_agent_factory_persists_custom_agent(tmp_path:Path):
    async def scenario():
        rt=await start_product_runtime(tmp_path,model_provider=MockModelProvider("Entrega suficientemente longa para validar o agente customizado e seu artifact."))
        try:
            created=rt.agent_factory.create(
                agent_id="custom.contracts",
                name="Contracts",
                mission="Analisar contratos fornecidos.",
                capabilities=["contracts"],
            )
            assert created["agent_id"]=="custom.contracts"
            assert rt.agent_registry.runtime("custom.contracts")
        finally:
            await rt.close()

        rt2=await start_product_runtime(tmp_path,model_provider=MockModelProvider("Entrega suficientemente longa para validar novamente o agente persistido."))
        try:
            assert rt2.agent_registry.runtime("custom.contracts")
            assert rt2.capabilities.resolve("contracts")["status"]=="available"
        finally:
            await rt2.close()
    asyncio.run(scenario())
