from __future__ import annotations

import argparse
import asyncio
import shutil
import tempfile
from pathlib import Path

from jarvis.app.bootstrap import start_runtime
from jarvis.core.events import Event


async def run(boots: int, events: int, tasks: int) -> None:
    base = Path(tempfile.mkdtemp(prefix="jarvis-phase0-stress-"))
    try:
        for _ in range(boots):
            rt = await start_runtime(base)
            health = rt.health.snapshot()
            assert health["status"] == "healthy", health
            await rt.close()

        rt = await start_runtime(base)
        try:
            for i in range(tasks):
                rt.tasks.create(
                    title=f"Stress task {i}",
                    objective="Foundation stress validation",
                    priority=i % 100,
                )
            assert rt.tasks.count() == tasks

            before_events = rt.events.count()
            for i in range(events):
                await rt.bus.publish(Event(
                    "stress.event",
                    run_id=rt.run_id,
                    payload={"i": i},
                ))
            assert rt.events.count() >= before_events + events
        finally:
            await rt.close()

        print(f"PASS: {boots} clean boots")
        print(f"PASS: {tasks} persisted tasks")
        print(f"PASS: {events} persisted events")
    finally:
        shutil.rmtree(base, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boots", type=int, default=50)
    parser.add_argument("--events", type=int, default=1000)
    parser.add_argument("--tasks", type=int, default=1000)
    args = parser.parse_args()
    asyncio.run(run(args.boots, args.events, args.tasks))


if __name__ == "__main__":
    main()
