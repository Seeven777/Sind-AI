from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict
from dataclasses import dataclass
from typing import Awaitable, Callable

from .events import Event

Handler = Callable[[Event], object | Awaitable[object]]


@dataclass(slots=True)
class Subscription:
    event_type: str
    handler: Handler
    _bus: "EventBus"
    active: bool = True

    def unsubscribe(self) -> None:
        if self.active:
            self._bus.unsubscribe(self)
            self.active = False


class EventBus:
    """In-process async event bus.

    Exact event subscriptions are supported plus "*" for every event.
    A broken subscriber never prevents the remaining subscribers from running.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._closed = False
        self._lock = asyncio.Lock()
        self._errors: list[tuple[str, Exception]] = []

    async def subscribe(self, event_type: str, handler: Handler) -> Subscription:
        if self._closed:
            raise RuntimeError("EventBus is closed")
        async with self._lock:
            self._handlers[event_type].append(handler)
        return Subscription(event_type, handler, self)

    def unsubscribe(self, subscription: Subscription) -> None:
        handlers = self._handlers.get(subscription.event_type, [])
        try:
            handlers.remove(subscription.handler)
        except ValueError:
            return

    async def publish(self, event: Event) -> None:
        if self._closed:
            raise RuntimeError("EventBus is closed")
        handlers = list(self._handlers.get(event.event_type, []))
        handlers += list(self._handlers.get("*", []))
        for handler in handlers:
            try:
                result = handler(event)
                if inspect.isawaitable(result):
                    await result
            except Exception as exc:  # subscriber isolation is deliberate
                self._errors.append((event.event_type, exc))

    @property
    def errors(self) -> tuple[tuple[str, Exception], ...]:
        return tuple(self._errors)

    async def close(self) -> None:
        async with self._lock:
            self._closed = True
            self._handlers.clear()
