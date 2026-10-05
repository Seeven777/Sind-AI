from __future__ import annotations

import asyncio
from types import SimpleNamespace

from jarvis.brain.orchestrator import JarvisOrchestrator
from jarvis.models import MockModelProvider, ModelRegistry, ModelRouter


class DummyMemory:
    def context(self, text, limit=4):
        return []


class DummyBus:
    async def publish(self, event):
        pass


class DummyTasks:
    pass


class DummyHermes:
    async def run(self, prompt):
        return SimpleNamespace(content=f"HERMES:{prompt}", metadata={"toolsets": "safe"})


class DummyMesh:
    hermes = DummyHermes()


def build(router):
    return JarvisOrchestrator(
        intent_router=SimpleNamespace(classify=lambda text: SimpleNamespace(name="chat", confidence=1, reason="test")),
        model_registry=router.registry,
        model_router=router,
        agent_registry=SimpleNamespace(),
        task_service=DummyTasks(),
        memory=DummyMemory(),
        bus=DummyBus(),
        ai_mesh=DummyMesh(),
    )


def test_hermes_direct_command_isolated_from_operator():
    models = ModelRegistry()
    models.register(MockModelProvider(), {"local": True, "paid": False, "capabilities": ["chat", "reasoning"]})
    router = ModelRouter("mock", "mock-model", models, privacy_mode="hybrid")
    result = asyncio.run(build(router).handle("/hermes planeje uma missão"))
    assert result["kind"] == "hermes"
    assert result["content"] == "HERMES:planeje uma missão"


def test_deep_command_uses_premium_provider_when_available():
    models = ModelRegistry()
    models.register(MockModelProvider("PREMIUM_OK"), {"local": False, "paid": False, "capabilities": ["reasoning"]})
    router = ModelRouter("mock", "mock-model", models, premium_provider="mock", privacy_mode="hybrid")
    result = asyncio.run(build(router).handle("/deep resolva isto"))
    assert result["kind"] == "deep"
    assert result["content"] == "PREMIUM_OK"
