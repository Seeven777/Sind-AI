import re
import time


class SwarmOrchestrator:
    """
    Coordenação multiagente leve e sequencial.

    Em hardware CPU-only, os agentes são papéis especializados executados um de
    cada vez sobre o pool de modelos local. Isso evita carregar vários modelos
    simultaneamente e ainda traz planejamento, especialização e revisão.
    """

    COMPLEX_MARKERS = (
        "planeje", "planejar", "estratégia", "estrategia", "projeto completo",
        "pesquise e", "analise e", "compare e", "crie e", "implemente",
        "automatize", "investigue", "faça tudo", "faca tudo", "do início ao fim",
        "do inicio ao fim", "múltiplas etapas", "multiplas etapas", "campanha completa",
        "plano completo", "sistema completo", "quero que você resolva", "quero que voce resolva",
        "use uma equipe", "equipe de agentes", "especialistas", "swarm",
    )

    def __init__(self, models, registry, blackboard, apprenticeship=None, config=None, experience=None):
        self.models = models
        self.registry = registry
        self.blackboard = blackboard
        self.apprenticeship = apprenticeship
        self.experience = experience
        self.config = config or {}
        self.max_specialists = int(self.config.get("swarm_max_specialists", 2))
        self.enabled = bool(self.config.get("swarm_enabled", True))
        self.review_enabled = bool(self.config.get("swarm_review_enabled", True))

    def set_experience(self, experience):
        self.experience = experience
        return {"ok": True, "adaptive_routing": bool(experience)}

    def should_swarm(self, text, tools=None):
        if not self.enabled:
            return False
        q = str(text or "").strip().lower()
        if not q:
            return False
        if any(x in q for x in ("use uma equipe", "equipe de agentes", "especialistas", "swarm")):
            return True
        score = 0
        score += sum(2 for x in self.COMPLEX_MARKERS if x in q)
        score += 1 if len(q) > 320 else 0
        score += 1 if q.count(" e ") >= 2 else 0
        score += 1 if len(tools or []) >= 4 else 0
        verbs = ("pesquis", "analise", "crie", "abra", "envie", "implemente", "publique", "compare", "automat")
        score += min(2, sum(1 for v in verbs if v in q))
        return score >= 3

    def _chat(self, role, goal, context, extra="", status=None):
        if status:
            status(f"Consultando especialista: {role.name}")
        prompt = (
            f"OBJETIVO DO USUÁRIO:\n{goal}\n\n"
            f"CONTEXTO DISPONÍVEL:\n{context[-4200:]}\n\n"
            f"{extra}\n"
            "Não exponha raciocínio interno. Seja conciso e operacional."
        )
        resp = self.models.chat(
            [
                {"role": "system", "content": role.prompt},
                {"role": "user", "content": prompt},
            ],
            user_text=goal,
            force=role.mode,
        )
        return ((resp.get("message") or {}).get("content") or "").strip()

    def prepare(self, goal, base_context="", status=None):
        procedure_context = {"items": [], "text": ""}
        if self.apprenticeship:
            try:
                procedure_context = self.apprenticeship.context(goal, limit=2, max_chars=2600)
            except Exception:
                procedure_context = {"items": [], "text": ""}

        candidate_roles = self.registry.select(
            goal, max_roles=max(self.max_specialists * 2, self.max_specialists)
        )
        if self.experience and candidate_roles:
            ranked=[]
            for index, role in enumerate(candidate_roles):
                try:
                    bonus=float(self.experience.agent_bonus(role.id))
                except Exception:
                    bonus=0.0
                # Semantic registry order remains dominant; experience fine-tunes ties.
                score=(-index)+(bonus*.35)
                ranked.append((score,role))
            ranked.sort(key=lambda x:-x[0])
            roles=[x[1] for x in ranked[:self.max_specialists]]
        else:
            roles=candidate_roles[:self.max_specialists]
        role_ids = ["planner"] + [r.id for r in roles]
        session_id = self.blackboard.start(goal, roles=role_ids)

        context = str(base_context or "")
        if procedure_context.get("text"):
            context += "\n\n" + procedure_context["text"]
            self.blackboard.add(
                session_id, "apprenticeship", "learned_procedure",
                procedure_context["text"],
                {"procedure_ids": [x.get("id") for x in procedure_context.get("items", [])]},
            )

        planner = self.registry.get("planner")
        if status:
            status("Definindo estratégia com Planner")
        try:
            plan = self._chat(planner, goal, context, status=None)
        except Exception as exc:
            plan = f"Planejamento especializado indisponível: {exc}"
        self.blackboard.add(session_id, "planner", "plan", plan)

        advisor_notes = []
        shared = f"{context}\n\nPLANO DO PLANNER:\n{plan}"
        for role in roles:
            try:
                note = self._chat(role, goal, shared, status=status)
            except Exception as exc:
                note = f"Especialista {role.name} indisponível nesta execução: {exc}"
            self.blackboard.add(session_id, role.id, "advice", note)
            advisor_notes.append((role.name, note))
            shared += f"\n\n{role.name.upper()}:\n{note}"

        compact = [f"PLANO:\n{plan}"]
        for name, note in advisor_notes:
            compact.append(f"ORIENTAÇÃO {name.upper()}:\n{note}")
        if procedure_context.get("text"):
            compact.append(procedure_context["text"])

        return {
            "ok": True,
            "session_id": session_id,
            "roles": role_ids,
            "plan": plan,
            "advisors": advisor_notes,
            "context": "\n\n".join(compact)[-6500:],
            "procedure_ids": [x.get("id") for x in procedure_context.get("items", []) if x.get("id")],
        }

    def solve(self, goal, base_context="", status=None):
        bundle = self.prepare(goal, base_context=base_context, status=status)
        executor_prompt = (
            "Você é o Executor do Jarvis. Use o plano e as orientações abaixo para responder ao objetivo do usuário. "
            "Não invente ações executadas. Se algo exigir uma ferramenta que não foi executada, diga isso de forma útil. "
            "Entregue uma resposta final completa e em português, sem chain-of-thought.\n\n"
            f"{bundle['context']}"
        )
        if status:
            status("Sintetizando trabalho dos especialistas")
        resp = self.models.chat(
            [
                {"role": "system", "content": executor_prompt},
                {"role": "user", "content": goal},
            ],
            user_text=goal,
            force="reason",
        )
        answer = ((resp.get("message") or {}).get("content") or "").strip()
        if not answer:
            answer = bundle.get("plan") or "Não consegui sintetizar uma resposta final."
        final = self.review(goal, answer, bundle=bundle, status=status)
        self.blackboard.add(bundle["session_id"], "executor", "answer", answer)
        self.blackboard.add(bundle["session_id"], "reviewer", "final", final)
        self.finish(bundle, status="completed", success=True)
        return {**bundle, "answer": final}

    def review(self, goal, candidate, bundle=None, tool_summaries=None, status=None):
        if not self.review_enabled:
            return candidate
        reviewer = self.registry.get("reviewer")
        context = (bundle or {}).get("context", "")
        if tool_summaries:
            context += "\n\nAÇÕES/EVIDÊNCIAS DO EXECUTOR:\n" + "\n".join(str(x) for x in tool_summaries[-8:])
        extra = f"RESPOSTA CANDIDATA:\n{candidate}"
        if status:
            status("Revisando entrega")
        try:
            reviewed = self._chat(reviewer, goal, context, extra=extra, status=None)
            if len(reviewed.strip()) >= 12:
                return reviewed.strip()
        except Exception:
            pass
        return candidate

    def finish(self, bundle, status="completed", success=True):
        if not bundle:
            return
        sid = bundle.get("session_id")
        if sid:
            self.blackboard.finish(sid, status)
        if self.apprenticeship:
            self.apprenticeship.record_use(bundle.get("procedure_ids", []), success=success)
        if self.experience:
            for role_id in bundle.get("roles", []):
                if role_id in {"planner"}:
                    continue
                try:
                    self.experience.record_agent_outcome(
                        role_id,
                        success=bool(success),
                        source_id=sid,
                        note=f"Swarm session {sid} finalizada como {status}.",
                    )
                except Exception:
                    pass

    def stats(self):
        data = self.blackboard.stats()
        data.update({
            "enabled": self.enabled,
            "max_specialists": self.max_specialists,
            "agents": len(self.registry.list()),
        })
        return data
