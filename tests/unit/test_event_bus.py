import asyncio
from jarvis.core.event_bus import EventBus
from jarvis.core.events import Event


def test_publish_and_subscriber_isolation():
    async def scenario():
        bus = EventBus()
        seen = []

        async def good(event):
            seen.append(event.event_type)

        def broken(event):
            raise RuntimeError("boom")

        await bus.subscribe("task.created", broken)
        await bus.subscribe("task.created", good)
        await bus.publish(Event("task.created"))
        assert seen == ["task.created"]
        assert len(bus.errors) == 1
        await bus.close()

    asyncio.run(scenario())


def test_unsubscribe():
    async def scenario():
        bus = EventBus()
        seen = []
        sub = await bus.subscribe("*", lambda e: seen.append(e.event_type))
        await bus.publish(Event("one"))
        sub.unsubscribe()
        await bus.publish(Event("two"))
        assert seen == ["one"]

    asyncio.run(scenario())
