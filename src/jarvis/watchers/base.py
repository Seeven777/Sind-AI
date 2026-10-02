from typing import Protocol
class Watcher(Protocol):
    watcher_id: str
    async def check(self) -> dict: ...
