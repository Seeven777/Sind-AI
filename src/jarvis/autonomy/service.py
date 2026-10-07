from __future__ import annotations

import asyncio
import json
import random
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

from jarvis.core.events import Event
from jarvis.models import ChatMessage
from jarvis.tasks import TaskStatus


_TOPIC_SEEDS = (
    "uma descoberta científica recente que muda nossa compreensão do mundo",
    "uma técnica pouco conhecida de engenharia de software",
    "um conceito fascinante de física ou astronomia",
    "uma inovação de interface homem-computador",
    "uma curiosidade histórica pouco conhecida",
    "um novo método de visualização de dados",
    "uma técnica de design de informação",
    "um avanço em robótica ou automação",
    "um padrão interessante encontrado na natureza",
    "uma ideia de arquitetura de sistemas distribuídos",
    "um tema de linguística ou evolução das línguas",
    "um conceito de matemática aplicada que tenha uso prático",
    "uma inovação open source interessante",
    "um estudo sobre tomada de decisão e organização do trabalho",
    "uma técnica de segurança e confiabilidade de software",
    "um método de memória computacional ou recuperação de contexto",
    "uma tecnologia emergente fora do ecossistema de IA",
    "um tema aleatório de arte, música ou cultura",
    "um processo industrial curioso ou eficiente",
    "uma descoberta geográfica, ambiental ou oceanográfica",
)


def _utcnow():
    return datetime.now(timezone.utc)


def _parse_iso(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def _extract_json(text):
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except Exception:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])
        raise


class AutonomyService:
    """Persistent, read-first autonomous life loop.

    The loop may explore the public web and learn without an explicit user order.
    It may propose self-improvements, but core changes are never silently applied.
    Approved proposals are turned into a normal Jarvis mission for implementation
    planning/review, preserving the project's observe/act/verify boundaries.
    """

    def __init__(
        self, *, repository, preferences, tool_executor, model_registry, model_router,
        memory, bus, task_service, agents, missions, foundation, project_root: Path,
        connector_service=None, capabilities=None
    ):
        self.repository = repository
        self.preferences = preferences
        self.tool_executor = tool_executor
        self.model_registry = model_registry
        self.model_router = model_router
        self.memory = memory
        self.bus = bus
        self.task_service = task_service
        self.agents = agents
        self.missions = missions
        self.foundation = foundation
        self.project_root = Path(project_root)
        self.connector_service = connector_service
        self.capabilities = capabilities
        self._lock = asyncio.Lock()

    def _pref(self, key, default):
        return self.preferences.get(f"autonomy.{key}", default)

    def status(self):
        daily = self.repository.get_state("daily_briefing", {}) or {}
        return {
            "schema": "jarvis.autonomy.v1",
            "enabled": bool(self._pref("enabled", True)),
            "curiosity_enabled": bool(self._pref("curiosity_enabled", True)),
            "self_improvement_enabled": bool(self._pref("self_improvement_enabled", True)),
            "agent_life_enabled": bool(self._pref("agent_life_enabled", True)),
            "voice_attention": bool(self._pref("voice_attention", True)),
            "location": str(self._pref("location", "São Paulo, SP")),
            "curiosity_interval_minutes": int(self._pref("curiosity_interval_minutes", 45)),
            "improvement_interval_minutes": int(self._pref("improvement_interval_minutes", 360)),
            "agent_life_interval_minutes": int(self._pref("agent_life_interval_minutes", 20)),
            "stats": self.repository.stats(),
            "last_curiosity_at": self.repository.get_state("last_curiosity_at"),
            "last_improvement_at": self.repository.get_state("last_improvement_at"),
            "last_agent_life_at": self.repository.get_state("last_agent_life_at"),
            "last_agent_life": self.repository.get_state("last_agent_life", {}),
            "last_briefing_at": self.repository.get_state("last_briefing_at"),
            "daily_briefing": daily,
            "recent_discoveries": self.repository.recent_discoveries(8),
            "improvements": self.repository.proposals(limit=8),
            "attention": self.repository.notifications(limit=12),
        }

    async def tick(self, *, force=False, scope=None):
        """Run one autonomous-life iteration.

        ``scope`` is intentionally narrow for manual UI actions. Background ticks
        use the complete loop, while a user pressing "Explorar agora" only
        starts curiosity instead of unexpectedly starting self-modification work.
        """
        if not bool(self._pref("enabled", True)):
            return {"status": "disabled"}
        allowed_scopes = {None, "all", "briefing", "curiosity", "agents", "improvement", "implementation"}
        if scope not in allowed_scopes:
            raise ValueError(f"Escopo autônomo inválido: {scope}")
        if self._lock.locked():
            return {"status": "busy"}
        selected = None if scope in {None, "all"} else scope
        async with self._lock:
            result = {"briefing": None, "curiosity": None, "agents": None, "improvement": None, "implementation": None}
            if selected in {None, "briefing"}:
                try:
                    if self._due("last_briefing_at", 60, force=force):
                        result["briefing"] = await self.refresh_daily_briefing(force=force)
                except Exception as exc:
                    await self._event("autonomy.briefing.failed", "warning", error=str(exc))
                    result["briefing"] = {"status": "failed", "error": str(exc)}
            if selected in {None, "curiosity"}:
                try:
                    if bool(self._pref("curiosity_enabled", True)) and self._due(
                        "last_curiosity_at", int(self._pref("curiosity_interval_minutes", 45)), force=force
                    ):
                        result["curiosity"] = await self.curiosity_cycle()
                except Exception as exc:
                    await self._event("autonomy.curiosity.failed", "warning", error=str(exc))
                    result["curiosity"] = {"status": "failed", "error": str(exc)}
            if selected in {None, "agents"}:
                try:
                    if bool(self._pref("agent_life_enabled", True)) and self._due(
                        "last_agent_life_at", int(self._pref("agent_life_interval_minutes", 20)), force=force
                    ):
                        result["agents"] = await self.agent_life_cycle()
                except Exception as exc:
                    await self._event("autonomy.agent_life.failed", "warning", error=str(exc))
                    result["agents"] = {"status": "failed", "error": str(exc)}
            if selected in {None, "improvement"}:
                try:
                    if bool(self._pref("self_improvement_enabled", True)) and self._due(
                        "last_improvement_at", int(self._pref("improvement_interval_minutes", 360)), force=force
                    ):
                        result["improvement"] = await self.self_improvement_cycle()
                except Exception as exc:
                    await self._event("autonomy.improvement.failed", "warning", error=str(exc))
                    result["improvement"] = {"status": "failed", "error": str(exc)}
            if selected in {None, "implementation"}:
                try:
                    result["implementation"] = await self._process_one_approved()
                except Exception as exc:
                    await self._event("autonomy.implementation.failed", "warning", error=str(exc))
                    result["implementation"] = {"status": "failed", "error": str(exc)}
            return result

    def _due(self, state_key, interval_minutes, *, force=False):
        if force:
            return True
        last = _parse_iso(self.repository.get_state(state_key))
        if last is None:
            return True
        return _utcnow() - last >= timedelta(minutes=max(1, int(interval_minutes)))

    async def _event(self, event_type, severity="info", **payload):
        await self.bus.publish(Event(event_type, severity=severity, payload=payload))

    async def _new_task(self, title, objective, priority=20, kind="autonomy"):
        task = await self.task_service.create(title, objective, priority, {"source": "autonomy", "kind": kind})
        await self.task_service.transition(task.task_id, TaskStatus.PLANNING)
        await self.task_service.transition(task.task_id, TaskStatus.READY)
        await self.task_service.transition(task.task_id, TaskStatus.RUNNING)
        return task

    async def _finish_task(self, task_id, error=None):
        if error:
            try:
                await self.task_service.transition(task_id, TaskStatus.FAILED, error=str(error))
            except Exception:
                pass
            return
        try:
            await self.task_service.transition(task_id, TaskStatus.VERIFYING)
            await self.task_service.transition(task_id, TaskStatus.COMPLETED)
        except Exception:
            pass

    def _provider(self, capability="reasoning"):
        route = self.model_router.route(capability=capability, privacy="local", budget="free")
        provider = self.model_registry.get(route.provider)
        return provider, route

    async def _model_text(self, prompt, *, system, capability="reasoning"):
        provider, route = self._provider(capability)
        response = await asyncio.to_thread(
            provider.chat, [ChatMessage("user", prompt)], model=route.model, system=system
        )
        return response.content.strip(), response

    async def _choose_topic(self):
        recent = self.repository.recent_topics(20)
        fallback_pool = [x for x in _TOPIC_SEEDS if x not in recent] or list(_TOPIC_SEEDS)
        fallback = random.choice(fallback_pool)
        try:
            prompt = (
                "Escolha UM assunto para explorar por curiosidade autônoma. Pode ser literalmente qualquer área. "
                "Não precisa estar ligado ao trabalho atual. Evite repetir os assuntos recentes. "
                "Responda somente com uma frase curta contendo o assunto.\n\n"
                "ASSUNTOS RECENTES:\n" + "\n".join(f"- {x}" for x in recent[:12])
            )
            text, _ = await self._model_text(
                prompt,
                system="Você é a curiosidade autônoma do Jarvis. Seja diverso, curioso e específico.",
                capability="fast",
            )
            topic = " ".join(text.replace("\n", " ").split())[:280].strip(" -\"'")
            return topic if len(topic) >= 8 else fallback
        except Exception:
            return fallback

    async def _web_bundle(self, query, *, fetch_limit=3):
        search = await self.tool_executor.execute("web.search", {"query": query, "limit": 7})
        if not search.success:
            return [], ""
        items = search.output.get("results", [])[:7]
        fetched = []
        blocks = []
        for item in items[:fetch_limit]:
            result = await self.tool_executor.execute("web.fetch", {"url": item.get("url")})
            record = {"title": item.get("title", ""), "url": item.get("url", "")}
            if result.success:
                record["page_title"] = result.output.get("title", "")
                record["content"] = result.output.get("content", "")[:6000]
            fetched.append(record)
            blocks.append(
                f"FONTE {len(blocks)+1}\nTÍTULO: {record.get('page_title') or record.get('title')}\n"
                f"URL: {record.get('url')}\nCONTEÚDO:\n{record.get('content','')}"
            )
        sources = fetched or items
        return sources, "\n\n".join(blocks)

    async def curiosity_cycle(self):
        topic = await self._choose_topic()
        task = await self._new_task("Exploração autônoma", topic, 15, "curiosity")
        await self._event("autonomy.curiosity.started", topic=topic, task_id=task.task_id)
        try:
            research = self.agents.runtime("research.general")
            result = await research.run(
                "Explore por curiosidade autônoma o tema abaixo. Não tente forçar relação com projetos atuais. "
                "Descubra algo concreto, atual ou surpreendente, valide com fontes e produza uma síntese curta.\n\n"
                f"TEMA: {topic}",
                task_id=task.task_id,
                context="Esta pesquisa foi iniciada pelo próprio Jarvis em segundo plano.",
                allow_external=True,
            )
            summary = result.content.strip()
            sources = (result.metadata or {}).get("sources") or []
            importance, level, title = await self._judge_discovery(topic, summary)
            item = self.repository.add_discovery(
                topic=topic, title=title, summary=summary, importance=importance,
                attention_level=level,
                sources=[{"title": x.get("title") or x.get("page_title"), "url": x.get("url")} for x in sources],
                metadata={"task_id": task.task_id, "artifact_id": result.artifact_id},
            )
            self.memory.remember(
                f"Descoberta autônoma — {title}\n{summary[:3500]}",
                memory_type="discovery", source="autonomy", source_ref=item["discovery_id"],
                confidence=.72 if sources else .45, scope="global", importance=importance / 100,
                metadata={"topic": topic, "attention_level": level},
            )
            if level in {"important", "critical"}:
                self.repository.add_notification(
                    kind="discovery", level=level, title=title,
                    message=self._short(summary), ref_type="discovery", ref_id=item["discovery_id"],
                )
            self.repository.set_state("last_curiosity_at", _utcnow().isoformat())
            await self._finish_task(task.task_id)
            await self._event(
                "autonomy.curiosity.completed", topic=topic, discovery_id=item["discovery_id"],
                importance=importance, attention_level=level,
            )
            return {"status": "completed", "discovery": item}
        except Exception as exc:
            self.repository.set_state("last_curiosity_at", _utcnow().isoformat())
            await self._finish_task(task.task_id, exc)
            raise

    async def agent_life_cycle(self):
        """Give every core role recurring, truthful background work.

        This is not visual theatre. Each state shown by HQ corresponds to an
        actual agent run or a verified low-risk Operator tool call. The cycle
        is intentionally read/prepare-first: it may inspect, classify, reason,
        propose and verify, but it does not grant itself write authority.
        """
        task = await self._new_task(
            "Ciclo de vida dos agentes",
            "Manter o Jarvis atento ao próprio contexto e distribuir trabalho útil entre seus agentes centrais.",
            18,
            "agent_life",
        )
        await self._event("autonomy.agent_life.started", task_id=task.task_id)
        outputs = []
        failures = []

        async def run_agent(agent_id, objective, context=""):
            try:
                agent = self.agents.runtime(agent_id)
                result = await agent.run(objective, task_id=task.task_id, context=context)
                outputs.append({
                    "agent_id": agent_id,
                    "success": bool(result.success),
                    "summary": self._short(result.summary, 1000),
                    "artifact_id": result.artifact_id,
                    "metadata": result.metadata or {},
                })
                return result
            except Exception as exc:
                failures.append({"agent_id": agent_id, "error": str(exc)[:900]})
                await self._event(
                    "autonomy.agent_life.agent_failed", "warning",
                    task_id=task.task_id, agent_id=agent_id, error=str(exc),
                )
                return None

        try:
            # Close the information loop before Inbox works. Connector failures
            # stay isolated: local Inbox/Calendar still remain usable.
            connector_sync = None
            if self.connector_service is not None:
                try:
                    connector_sync = await self.connector_service.sync_all()
                except Exception as exc:
                    failures.append({"agent_id": "administration.inbox", "error": f"connector sync: {exc}"[:900]})

            # Sensors work in parallel. These are deterministic/read-only roles,
            # so parallelism gives the Office real concurrent activity without
            # overloading the local LLM.
            inbox, memory = await asyncio.gather(
                run_agent(
                    "administration.inbox",
                    "Faça a triagem do que entrou pelos connectors autorizados. Priorize sem responder, enviar ou alterar nada externamente.",
                    "Ciclo autônomo read-only. A caixa de entrada serve como sensor do ambiente.",
                ),
                run_agent(
                    "memory.curator",
                    "Audite a memória do Jarvis para manter contexto útil, detectar duplicidades e sinalizar informação antiga de baixa importância.",
                    "Não apague memória automaticamente. Produza evidência para futuras decisões.",
                ),
            )

            health = self.foundation.health.snapshot()
            recent_events = self.foundation.events.recent(40)
            alerts = [x for x in recent_events if x.get("severity") in {"warning", "error", "critical"}][:10]
            discoveries = self.repository.recent_discoveries(5)
            inventory = self.capabilities.inventory() if self.capabilities is not None else {}
            sensor_context = (
                "ESTADO DO SISTEMA:\n" + json.dumps(health, ensure_ascii=False)[:3600] +
                "\n\nALERTAS RECENTES:\n" + json.dumps(alerts, ensure_ascii=False)[:4200] +
                "\n\nDESCOBERTAS AUTÔNOMAS:\n" + json.dumps(discoveries, ensure_ascii=False)[:3200] +
                "\n\nCAPACIDADES REGISTRADAS:\n" + json.dumps(inventory, ensure_ascii=False)[:4200] +
                "\n\nINBOX:\n" + (self._short(inbox.summary, 1800) if inbox else "indisponível") +
                "\n\nMEMÓRIA:\n" + (self._short(memory.summary, 1800) if memory else "indisponível")
            )

            async def run_operator_checks():
                operator = self.agents.runtime("operations.operator")
                checks = []
                for tool_id, payload in (
                    ("system.time", {}),
                    ("files.list_directory", {"path": str(self.project_root), "limit": 30}),
                ):
                    try:
                        result = await operator.execute(tool_id, payload, task_id=task.task_id)
                        checks.append({
                            "tool_id": tool_id,
                            "success": bool(result.success),
                            "status": (result.metadata or {}).get("status"),
                            "summary": self._short(result.summary, 500),
                        })
                        if not result.success:
                            failures.append({"agent_id": "operations.operator", "error": result.summary[:900]})
                    except Exception as exc:
                        failures.append({"agent_id": "operations.operator", "error": str(exc)[:900]})
                outputs.append({
                    "agent_id": "operations.operator",
                    "success": bool(checks) and all(x["success"] for x in checks),
                    "summary": " · ".join(x["summary"] for x in checks),
                    "metadata": {"safe_read_checks": checks},
                })
                return checks

            # Analyst and Operator can work at the same time: one reasons about
            # the sensor state while the other verifies low-risk runtime facts.
            analyst, operator_checks = await asyncio.gather(
                run_agent(
                    "intelligence.analyst",
                    "Faça uma leitura operacional curta do Jarvis agora. Identifique no máximo três sinais relevantes: gargalo, risco, oportunidade ou prioridade. Não invente falhas.",
                    sensor_context,
                ),
                run_operator_checks(),
            )

            analysis_context = self._short(analyst.summary, 3200) if analyst else sensor_context[:3200]
            # Creator and Developer receive the same verified analysis and run
            # concurrently. This produces truthful multi-agent activity in HQ.
            creator, developer = await asyncio.gather(
                run_agent(
                    "creative.creator",
                    "Transforme a leitura operacional atual em UMA iniciativa pequena e útil que melhore a experiência, organização ou capacidade do Jarvis sem executar alterações. Seja concreto.",
                    analysis_context,
                ),
                run_agent(
                    "engineering.developer",
                    "Faça uma inspeção de manutenção do próprio Jarvis. Escolha no máximo um ponto técnico verificável para acompanhar ou testar. Não modifique o core e não afirme execução que não ocorreu.",
                    analysis_context + "\n\nMAPA DO CÓDIGO:\n" + self._source_manifest()[:4200],
                ),
            )

            review_context = "\n\n".join(
                f"{x['agent_id']}: {x.get('summary','')}" for x in outputs[-7:]
            )
            reviewer = await run_agent(
                "review.verifier",
                "Revise este ciclo autônomo dos agentes. Verifique se houve trabalho útil, se os achados possuem suporte no contexto e se nenhuma ação externa não autorizada foi executada.",
                review_context[:8000],
            )

            result = {
                "status": "degraded" if failures else "completed",
                "task_id": task.task_id,
                "agents": outputs,
                "failures": failures,
                "connector_sync": connector_sync,
                "review_passed": bool(reviewer and "VERDICT: PASS" in reviewer.summary.upper()),
                "completed_at": _utcnow().isoformat(),
            }
            self.repository.set_state("last_agent_life_at", _utcnow().isoformat())
            self.repository.set_state("last_agent_life", result)
            await self._finish_task(task.task_id)
            await self._event(
                "autonomy.agent_life.completed",
                "warning" if failures else "info",
                task_id=task.task_id,
                agents_completed=sum(1 for x in outputs if x.get("success")),
                failures=len(failures),
            )
            return result
        except Exception as exc:
            self.repository.set_state("last_agent_life_at", _utcnow().isoformat())
            self.repository.set_state("last_agent_life", {
                "status": "failed", "task_id": task.task_id, "error": str(exc),
                "agents": outputs, "failures": failures,
            })
            await self._finish_task(task.task_id, exc)
            raise

    async def _judge_discovery(self, topic, summary):
        fallback_importance = 35
        fallback_level = "ambient"
        fallback_title = "Descoberta: " + " ".join(topic.split())[:110]
        try:
            text, _ = await self._model_text(
                f"TEMA: {topic}\n\nDESCOBERTA:\n{summary[:6500]}",
                system=(
                    "Avalie uma descoberta feita autonomamente pelo Jarvis. Decida sozinho se merece chamar a atenção do usuário. "
                    "Use CRITICAL apenas para algo realmente urgente/acionável, IMPORTANT para algo muito relevante ou surpreendente, "
                    "e AMBIENT para aprendizado normal. Responda SOMENTE JSON: "
                    '{"title":"...","importance":0,"attention_level":"ambient|important|critical"}'
                ),
                capability="fast",
            )
            data = _extract_json(text)
            importance = max(0, min(100, int(data.get("importance", fallback_importance))))
            level = str(data.get("attention_level", fallback_level)).lower()
            if level not in {"ambient", "important", "critical"}:
                level = "important" if importance >= 75 else "ambient"
            if importance >= 92:
                level = "critical"
            elif importance >= 72 and level == "ambient":
                level = "important"
            title = " ".join(str(data.get("title") or fallback_title).split())[:180]
            return importance, level, title
        except Exception:
            return fallback_importance, fallback_level, fallback_title

    async def refresh_daily_briefing(self, *, force=False):
        location = str(self._pref("location", "São Paulo, SP"))
        today = datetime.now().astimezone().strftime("%Y-%m-%d")
        weather_sources, weather_context = await self._web_bundle(
            f"previsão do tempo hoje {location} {today}", fetch_limit=2
        )
        news_sources, news_context = await self._web_bundle(
            f"principais notícias Brasil mundo hoje {today}", fetch_limit=3
        )
        weather_summary = "Previsão indisponível no momento."
        news_summary = []
        try:
            text, _ = await self._model_text(
                f"LOCAL: {location}\nDATA: {today}\n\nFONTES:\n{weather_context}",
                system=(
                    "Extraia uma previsão do tempo curta e conservadora usando apenas as fontes. "
                    "Não invente temperatura. Responda em uma única frase em português."
                ),
                capability="fast",
            )
            if text:
                weather_summary = " ".join(text.split())[:320]
        except Exception:
            if weather_sources:
                weather_summary = weather_sources[0].get("title") or weather_summary
        try:
            text, _ = await self._model_text(
                f"DATA: {today}\n\nFONTES:\n{news_context}",
                system=(
                    "Escolha até 5 notícias diferentes e relevantes usando apenas as fontes fornecidas. "
                    "Responda SOMENTE JSON no formato {\"items\":[{\"title\":\"...\",\"summary\":\"...\"}]}"
                ),
                capability="fast",
            )
            data = _extract_json(text)
            news_summary = [
                {"title": str(x.get("title") or "")[:220], "summary": str(x.get("summary") or "")[:420]}
                for x in (data.get("items") or [])[:5] if isinstance(x, dict) and x.get("title")
            ]
        except Exception:
            news_summary = [
                {"title": str(x.get("title") or x.get("page_title") or "Notícia")[:220], "summary": ""}
                for x in news_sources[:5]
            ]
        improvements = self.repository.proposals("pending", 5)
        discoveries = self.repository.recent_discoveries(5)
        daily = {
            "date": today,
            "generated_at": _utcnow().isoformat(),
            "location": location,
            "weather": {"summary": weather_summary, "sources": self._source_links(weather_sources)},
            "news": news_summary,
            "news_sources": self._source_links(news_sources),
            "discoveries": discoveries,
            "improvements": improvements,
        }
        self.repository.set_state("daily_briefing", daily)
        self.repository.set_state("last_briefing_at", _utcnow().isoformat())
        await self._event("autonomy.briefing.updated", location=location, news=len(news_summary))
        return daily

    async def self_improvement_cycle(self):
        health = self.foundation.health.snapshot()
        recent_events = self.foundation.events.recent(30)
        errors = [x for x in recent_events if x.get("severity") in {"warning", "error", "critical"}][:8]
        source_manifest = self._source_manifest()
        task = await self._new_task(
            "Autoavaliação do Jarvis", "Identificar uma melhoria concreta para o próprio sistema", 25, "self_improvement"
        )
        await self._event("autonomy.improvement.started", task_id=task.task_id)
        try:
            developer = self.agents.runtime("engineering.developer")
            objective = (
                "Você está fazendo uma autoavaliação do próprio Jarvis. Escolha UMA melhoria pequena, concreta e testável que aumente "
                "capacidade, confiabilidade, autonomia, experiência ou observabilidade. Não altere arquivos. Prepare uma proposta para aprovação humana. "
                "Evite repetir algo que já esteja implementado.\n\n"
                f"HEALTH:\n{json.dumps(health, ensure_ascii=False)[:5000]}\n\n"
                f"EVENTOS COM ALERTA:\n{json.dumps(errors, ensure_ascii=False)[:5500]}\n\n"
                f"MAPA DO CÓDIGO:\n{source_manifest[:6500]}\n\n"
                "No início da resposta use exatamente:\nTITLE: ...\nRISK: low|medium|high\nSUMMARY: ...\n"
                "Depois explique diagnóstico, plano, arquivos prováveis, testes e critério de sucesso."
            )
            result = await developer.run(objective, task_id=task.task_id, context="Autoevolução supervisionada: nenhuma alteração no core pode ser aplicada sem aprovação.")
            title, summary, risk = self._parse_proposal_headers(result.content)
            reviewer = self.agents.runtime("review.verifier")
            review = await reviewer.run(
                "Revise esta proposta de auto-melhoria do Jarvis. Verifique se é concreta, segura, não duplica o que já existe e possui teste verificável.",
                task_id=task.task_id, context=result.content,
            )
            if "VERDICT: PASS" not in review.content.upper():
                summary = summary + " — Reviewer pediu revisão antes da implementação."
                risk = "medium" if risk == "low" else risk
            proposal = self.repository.add_proposal(
                title=title, summary=summary, rationale=result.content, risk=risk,
                plan=["diagnóstico", "implementação em missão supervisionada", "testes", "revisão", "aprovação final"],
                metadata={
                    "task_id": task.task_id,
                    "developer_artifact_id": result.artifact_id,
                    "review_artifact_id": review.artifact_id,
                    "review_pass": "VERDICT: PASS" in review.content.upper(),
                },
            )
            self.repository.add_notification(
                kind="improvement", level="important", title="Nova melhoria proposta",
                message=f"{proposal['title']} — aguarda sua aprovação.", ref_type="improvement", ref_id=proposal["proposal_id"],
            )
            self.repository.set_state("last_improvement_at", _utcnow().isoformat())
            await self._finish_task(task.task_id)
            await self._event("autonomy.improvement.proposed", proposal_id=proposal["proposal_id"], title=proposal["title"])
            return {"status": "proposed", "proposal": proposal}
        except Exception as exc:
            self.repository.set_state("last_improvement_at", _utcnow().isoformat())
            await self._finish_task(task.task_id, exc)
            raise

    def _source_manifest(self):
        src = self.project_root / "src" / "jarvis"
        if not src.exists():
            return "Código-fonte não localizado nesta instalação."
        rows = []
        for path in sorted(src.rglob("*.py"))[:180]:
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            rows.append(f"{path.relative_to(self.project_root)} — {len(text.splitlines())} linhas")
        return "\n".join(rows)

    @staticmethod
    def _parse_proposal_headers(content):
        title = "Melhoria autônoma proposta"
        summary = "Jarvis identificou uma oportunidade de melhoria que requer aprovação."
        risk = "medium"
        for line in str(content).splitlines()[:20]:
            upper = line.upper()
            if upper.startswith("TITLE:"):
                title = line.split(":", 1)[1].strip()[:220] or title
            elif upper.startswith("SUMMARY:"):
                summary = line.split(":", 1)[1].strip()[:700] or summary
            elif upper.startswith("RISK:"):
                candidate = line.split(":", 1)[1].strip().lower()
                if candidate in {"low", "medium", "high"}:
                    risk = candidate
        return title, summary, risk

    async def approve_improvement(self, proposal_id):
        proposal = self.repository.get_proposal(proposal_id)
        if proposal is None:
            raise KeyError(proposal_id)
        if proposal["status"] not in {"pending", "failed"}:
            return proposal
        updated = self.repository.set_proposal_status(proposal_id, "approved")
        await self._event("autonomy.improvement.approved", proposal_id=proposal_id, title=proposal["title"])
        return updated

    async def reject_improvement(self, proposal_id):
        proposal = self.repository.get_proposal(proposal_id)
        if proposal is None:
            raise KeyError(proposal_id)
        updated = self.repository.set_proposal_status(proposal_id, "rejected")
        await self._event("autonomy.improvement.rejected", proposal_id=proposal_id, title=proposal["title"])
        return updated

    async def _process_one_approved(self):
        items = self.repository.proposals("approved", 1)
        if not items:
            return {"status": "idle"}
        proposal = items[0]
        pid = proposal["proposal_id"]
        self.repository.set_proposal_status(pid, "implementing")
        await self._event("autonomy.implementation.started", proposal_id=pid, title=proposal["title"])
        try:
            objective = (
                "Prepare a implementação desta melhoria do próprio Jarvis como uma missão supervisionada. "
                "Não declare mudanças que não tenham sido realmente feitas. Como o core não pode ser alterado silenciosamente, "
                "a saída deve ser uma implementação/patch plenamente especificado, testes e validação para aplicação humana posterior.\n\n"
                f"PROPOSTA:\n{proposal['title']}\n{proposal['rationale']}"
            )
            result = await self.missions.run(objective, title=f"Auto-melhoria: {proposal['title']}")
            updated = self.repository.set_proposal_status(
                pid, "prepared", {"mission_result": self._compact_mission_result(result)}
            )
            self.repository.add_notification(
                kind="improvement_ready", level="important", title="Melhoria preparada para aplicação",
                message=f"{proposal['title']} terminou a missão de implementação e revisão.", ref_type="improvement", ref_id=pid,
            )
            await self._event("autonomy.implementation.prepared", proposal_id=pid, title=proposal["title"])
            return {"status": "prepared", "proposal": updated}
        except Exception as exc:
            self.repository.set_proposal_status(pid, "failed", {"implementation_error": str(exc)})
            await self._event("autonomy.implementation.failed", "error", proposal_id=pid, error=str(exc))
            return {"status": "failed", "proposal_id": pid, "error": str(exc)}

    @staticmethod
    def _compact_mission_result(result):
        if not isinstance(result, dict):
            return {"result": str(result)[:1000]}
        keep = {}
        for key in ("mission_id", "task_id", "status", "artifact_id", "artifact_path", "review"):
            if key in result:
                value = result[key]
                keep[key] = value if not isinstance(value, str) else value[:1800]
        return keep

    def acknowledge(self, notification_id):
        item = self.repository.acknowledge(notification_id)
        if item is None:
            raise KeyError(notification_id)
        return item

    @staticmethod
    def _short(text, limit=360):
        return " ".join(str(text or "").split())[:limit]

    @staticmethod
    def _source_links(items):
        return [
            {"title": str(x.get("page_title") or x.get("title") or "Fonte")[:220], "url": x.get("url")}
            for x in items[:6] if x.get("url")
        ]
