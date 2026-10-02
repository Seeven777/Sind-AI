import asyncio
from pathlib import Path

import pytest

from jarvis.app.bootstrap import start_runtime
from jarvis.core.errors import LockError


def test_second_instance_is_rejected_without_fake_run(tmp_path: Path):
    async def scenario():
        rt1 = await start_runtime(tmp_path)
        try:
            with pytest.raises(LockError):
                await start_runtime(tmp_path)
            rows = rt1.database.conn().execute(
                "SELECT run_id FROM system_runs ORDER BY started_at"
            ).fetchall()
            assert len(rows) == 1
            assert rows[0]["run_id"] == rt1.run_id
        finally:
            await rt1.close()

    asyncio.run(scenario())
