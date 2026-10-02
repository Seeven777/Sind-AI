import asyncio
from pathlib import Path

from jarvis.app.bootstrap import start_runtime
from jarvis.core.events import Event


def test_event_is_persisted(tmp_path: Path):
    async def scenario():
        rt = await start_runtime(tmp_path)
        try:
            await rt.bus.publish(Event("demo.event", run_id=rt.run_id, payload={"x": 1}))
            rows = rt.database.conn().execute(
                "SELECT * FROM events WHERE event_type='demo.event'"
            ).fetchall()
            assert len(rows) == 1
        finally:
            await rt.close()

    asyncio.run(scenario())
