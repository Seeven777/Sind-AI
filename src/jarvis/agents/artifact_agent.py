from __future__ import annotations

import asyncio

from jarvis.agents.base import AgentCard, AgentResult
from jarvis.core.events import Event
from jarvis.models import ChatMessage


class ArtifactAgent:
    """Reusable specialist that converts an input brief into one persisted artifact.

    The runtime deliberately performs one controlled recovery attempt when a
    local model returns an empty/too-short final answer or has a transient
    generation failure. This avoids leaving core agents permanently failed for
    recoverable Ollama hiccups while preserving the real error if both attempts
    fail.
    """

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

    async def _generate(self, provider, route, prompt: str):
        return await asyncio.to_thread(
            provider.chat,
            [ChatMessage("user", prompt)],
            model=route.model,
            system=self.system_prompt,
        )

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

            first_error = None
            response = None
            try:
                response = await self._generate(provider, route, prompt)
                if len(response.content.strip()) < 40:
                    first_error = RuntimeError(f"{self.card.name} produziu uma entrega insuficiente.")
                    response = None
            except Exception as exc:
                first_error = exc

            if response is None:
                self.agent_runs.update_activity(rid, "Recuperando geração", 0.56)
                await self.bus.publish(Event(
                    "agent.progress",
                    severity="warning",
                    task_id=task_id,
                    agent_id=self.card.agent_id,
                    payload={
                        "agent_run_id": rid,
                        "progress": 0.56,
                        "activity": "Recuperando geração",
                        "reason": str(first_error)[:500] if first_error else "resposta curta",
                    },
                ))
                retry_prompt = (
                    prompt +
                    "\n\nRECOVERY DIRECTIVE: entregue agora uma RESPOSTA FINAL completa, concreta e útil. "
                    "Não exponha raciocínio interno. Não responda apenas com uma frase curta."
                )
                response = await self._generate(provider, route, retry_prompt)

            content = response.content.strip()
            if len(content) < 40:
                raise RuntimeError(f"{self.card.name} produziu uma entrega insuficiente após recuperação.")

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
                    "recovered": bool(first_error),
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
                {
                    "model": response.model,
                    "provider": response.provider,
                    "recovered": bool(first_error),
                },
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
