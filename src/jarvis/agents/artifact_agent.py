from __future__ import annotations

import asyncio

from jarvis.agents.base import AgentCard, AgentResult
from jarvis.core.events import Event
from jarvis.models import ChatMessage


class ArtifactAgent:
    """Reusable specialist that converts an input brief into one persisted artifact."""

    card: AgentCard
    system_prompt: str
    artifact_name: str

    def __init__(
        self, *,
        model_registry,
        model_router,
        artifact_store,
        agent_runs,
        bus,
    ):
        self.model_registry = model_registry
        self.model_router = model_router
        self.artifact_store = artifact_store
        self.agent_runs = agent_runs
        self.bus = bus

    async def run(self, objective: str, *, task_id: str, context: str = "") -> AgentResult:
        route = self.model_router.route(capability=self.card.model_capability, privacy="local")
        provider = self.model_registry.get(route.provider)
        rid = self.agent_runs.start(
            self.card.agent_id,
            task_id,
            route.model,
            {"objective": objective, "context_chars": len(context)},
        )
        self.agent_runs.update_activity(rid, "Preparando trabalho", 0.08)
        await self.bus.publish(Event(
            "agent.started",
            task_id=task_id,
            agent_id=self.card.agent_id,
            payload={"agent_run_id": rid, "model": route.model, "activity": "Preparando trabalho"},
        ))
        try:
            prompt = objective if not context else (
                f"MISSÃO:\n{objective}\n\n"
                f"ARTIFACT/CONTEXTO RECEBIDO DO AGENTE ANTERIOR:\n{context}"
            )
            self.agent_runs.update_activity(rid, "Raciocinando", 0.35)
            await self.bus.publish(Event(
                "agent.progress",
                task_id=task_id,
                agent_id=self.card.agent_id,
                payload={"agent_run_id": rid, "progress": 0.35, "activity": "Raciocinando"},
            ))
            response = await asyncio.to_thread(
                provider.chat,
                [ChatMessage("user", prompt)],
                model=route.model,
                system=self.system_prompt,
            )
            content = response.content.strip()
            if len(content) < 40:
                raise RuntimeError(f"{self.card.name} produziu uma entrega insuficiente.")

            self.agent_runs.update_activity(rid, "Salvando artifact", 0.82)
            artifact = self.artifact_store.write_text(
                task_id=task_id,
                agent_id=self.card.agent_id,
                name=self.artifact_name,
                content=content,
                metadata={
                    "provider": response.provider,
                    "model": response.model,
                    "route_reason": route.reason,
                },
            )
            self.agent_runs.finish(rid, artifact_id=artifact["artifact_id"])
            await self.bus.publish(Event(
                "artifact.created",
                task_id=task_id,
                agent_id=self.card.agent_id,
                payload={
                    "artifact_id": artifact["artifact_id"],
                    "name": artifact["name"],
                    "path": artifact["path"],
                },
            ))
            await self.bus.publish(Event(
                "agent.completed",
                task_id=task_id,
                agent_id=self.card.agent_id,
                payload={
                    "agent_run_id": rid,
                    "artifact_id": artifact["artifact_id"],
                    "activity": "Concluído",
                },
            ))
            return AgentResult(
                True,
                content,
                artifact["artifact_id"],
                artifact["path"],
                {"model": response.model, "provider": response.provider},
            )
        except Exception as exc:
            self.agent_runs.finish(rid, error=str(exc))
            await self.bus.publish(Event(
                "agent.failed",
                severity="error",
                task_id=task_id,
                agent_id=self.card.agent_id,
                payload={"agent_run_id": rid, "error": str(exc)},
            ))
            raise
