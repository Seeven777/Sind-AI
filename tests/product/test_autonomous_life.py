from __future__ import annotations

import asyncio

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models.mock import MockModelProvider


def test_autonomy_repository_and_status(tmp_path):
    async def scenario():
        rt = await start_product_runtime(tmp_path, model_provider=MockModelProvider())
        try:
            status = rt.autonomy.status()
            assert status["schema"] == "jarvis.autonomy.v1"
            assert status["enabled"] is True
            assert status["curiosity_enabled"] is True

            discovery = rt.autonomy_repository.add_discovery(
                topic="teste de curiosidade",
                title="Uma descoberta verificável",
                summary="Conteúdo de teste",
                importance=81,
                attention_level="important",
            )
            assert discovery["importance"] == 81
            assert rt.autonomy_repository.recent_discoveries(1)[0]["discovery_id"] == discovery["discovery_id"]

            proposal = rt.autonomy_repository.add_proposal(
                title="Melhorar observabilidade",
                summary="Adicionar uma métrica",
                rationale="Há uma lacuna observável.",
                risk="low",
            )
            assert proposal["status"] == "pending"
            await rt.autonomy.approve_improvement(proposal["proposal_id"])
            assert rt.autonomy_repository.get_proposal(proposal["proposal_id"])["status"] == "approved"

            note = rt.autonomy_repository.add_notification(
                kind="discovery", level="important", title="Senhor", message="Algo merece atenção"
            )
            assert rt.autonomy_repository.notifications(limit=1)[0]["notification_id"] == note["notification_id"]
            rt.autonomy.acknowledge(note["notification_id"])
            assert rt.autonomy_repository.get_notification(note["notification_id"])["status"] == "acknowledged"
        finally:
            await rt.close()

    asyncio.run(scenario())
