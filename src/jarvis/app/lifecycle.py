from __future__ import annotations

import asyncio
from pathlib import Path

from .bootstrap import start_runtime


async def run_forever(data_dir: Path | None = None) -> None:
    runtime = await start_runtime(data_dir)
    stop = asyncio.Event()
    try:
        print("JARVIS NEXT")
        print("Foundation Runtime")
        print()
        health = runtime.health.snapshot()
        print(f"Database............. {health['database'].upper()}")
        print(f"Event Bus............ {health['event_bus'].upper()}")
        print(f"Task Repository...... {health['task_repository'].upper()}")
        print(f"Recovery............. OK")
        print()
        print(f"Run: {runtime.run_id}")
        print(f"Status: {health['status'].upper()}")
        print()
        print("Jarvis Core ready. Press Ctrl+C to stop.")
        await stop.wait()
    finally:
        await runtime.close()


async def run_once(data_dir: Path | None = None) -> dict:
    runtime = await start_runtime(data_dir)
    try:
        return runtime.health.snapshot()
    finally:
        await runtime.close()
