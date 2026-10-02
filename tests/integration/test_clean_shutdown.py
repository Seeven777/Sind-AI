import asyncio
from pathlib import Path

from jarvis.app.bootstrap import start_runtime


def test_clean_shutdown_is_recorded(tmp_path: Path):
    async def scenario():
        rt = await start_runtime(tmp_path)
        run_id = rt.run_id
        await rt.close()

        # Reopen through a new runtime and inspect the prior run.
        rt2 = await start_runtime(tmp_path)
        try:
            row = rt2.database.conn().execute(
                "SELECT shutdown_clean, stopped_at FROM system_runs WHERE run_id=?",
                (run_id,),
            ).fetchone()
            assert row["shutdown_clean"] == 1
            assert row["stopped_at"] is not None
            assert rt2.health.last_recovery_count == 0
        finally:
            await rt2.close()

    asyncio.run(scenario())
