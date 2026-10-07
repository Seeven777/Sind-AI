import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_agent_life_cycle_gives_real_work_to_core_roles(tmp_path: Path):
    async def scenario():
        model = MockModelProvider(
            'VERDICT: PASS. Análise simulada completa e suficientemente detalhada '
            'para validar o ciclo autônomo de agentes com evidência controlada.'
        )
        rt = await start_product_runtime(tmp_path, model_provider=model)
        try:
            result = await rt.autonomy.agent_life_cycle()
            ids = {row['agent_id'] for row in result['agents'] if row['success']}
            assert result['status'] == 'completed'
            assert result['review_passed'] is True
            assert ids == {
                'administration.inbox',
                'memory.curator',
                'intelligence.analyst',
                'creative.creator',
                'engineering.developer',
                'operations.operator',
                'review.verifier',
            }

            # Completed agents are available again, not stuck on fake 0%/error.
            hq = rt.hq.snapshot()
            rows = {a['id']: a for room in hq['departments'].values() for a in room}
            for agent_id in ids:
                assert rows[agent_id]['status'] == 'idle'
                assert rows[agent_id]['progress'] is None
                assert rows[agent_id]['health'] == 'healthy'
        finally:
            await rt.close()

    asyncio.run(scenario())
