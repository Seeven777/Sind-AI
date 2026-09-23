import re


class DemonstrationTeacher:
    """Natural-language bridge for Observe & Learn.

    1.9 behavior (explicit teaching) is preserved.
    Phase 1 adds direct commands for the opt-in personal context observer so the
    feature can be tested without changing core/agent.py or the main UI.
    """

    START_PATTERNS = (
        r"^observe enquanto eu faço\s+(.+)$",
        r"^observe enquanto eu faco\s+(.+)$",
        r"^aprenda observando(?: como)?\s+(.+)$",
        r"^vou te mostrar(?: como)?\s+(.+)$",
        r"^quero te mostrar(?: como)?\s+(.+)$",
    )
    FINISH = (
        "terminei a demonstração",
        "terminei a demonstracao",
        "finalizar demonstração",
        "finalizar demonstracao",
        "fim da demonstração",
        "fim da demonstracao",
    )
    CANCEL = (
        "cancelar demonstração",
        "cancelar demonstracao",
        "pare de observar a demonstração",
        "pare de observar a demonstracao",
    )

    PASSIVE_START = (
        "ative o aprendizado contínuo",
        "ative o aprendizado continuo",
        "ative aprendizado contínuo",
        "ative aprendizado continuo",
        "ative o observador pessoal",
        "ative observador pessoal",
        "comece a observar meu trabalho",
        "observe meu trabalho continuamente",
        "comece a aprender meu contexto",
    )
    PASSIVE_STOP = (
        "desative o aprendizado contínuo",
        "desative o aprendizado continuo",
        "desative aprendizado contínuo",
        "desative aprendizado continuo",
        "desative o observador pessoal",
        "pare de observar meu trabalho",
        "pare o observador pessoal",
    )
    PASSIVE_STATUS = (
        "status do observador pessoal",
        "status do aprendizado contínuo",
        "status do aprendizado continuo",
        "o observador pessoal está ativo",
        "o observador pessoal esta ativo",
    )
    CONTEXT_QUERIES = (
        "o que estou fazendo agora",
        "em que estou trabalhando agora",
        "qual é meu contexto atual",
        "qual e meu contexto atual",
        "qual aplicativo estou usando",
        "onde estou trabalhando agora",
    )
    PATTERN_QUERIES = (
        "quais padrões de trabalho você percebeu",
        "quais padroes de trabalho voce percebeu",
        "o que você aprendeu observando meu trabalho",
        "o que voce aprendeu observando meu trabalho",
        "mostre padrões da minha atividade",
        "mostre padroes da minha atividade",
    )
    OPERATIONAL_CONTEXT_QUERIES = (
        "qual é meu contexto operacional",
        "qual e meu contexto operacional",
        "me dê meu contexto operacional",
        "me de meu contexto operacional",
        "contexto operacional",
        "em que eu estava trabalhando",
        "onde eu parei",
        "continue de onde parei",
    )
    PROCEDURE_QUERIES = (
        "quais procedimentos você aprendeu",
        "quais procedimentos voce aprendeu",
        "quais rotinas você aprendeu",
        "quais rotinas voce aprendeu",
        "mostre sua memória procedural",
        "mostre sua memoria procedural",
    )
    EXPERT_QUERIES = (
        "quais aplicativos você conhece",
        "quais aplicativos voce conhece",
        "quais especialistas você tem",
        "quais especialistas voce tem",
        "mostre sua experiência por aplicativo",
        "mostre sua experiencia por aplicativo",
    )
    LEARNING_QUERIES = (
        "status do aprendizado pessoal",
        "status do aprendizado",
        "o que você já aprendeu comigo",
        "o que voce ja aprendeu comigo",
        "quão autônomo você está",
        "quao autonomo voce esta",
        "qual seu nível de autonomia",
        "qual seu nivel de autonomia",
    )

    def __init__(self, observe_engine, skill_store):
        self.observe = observe_engine
        self.skills = skill_store
        self._name = None

    @staticmethod
    def _clean(text):
        return str(text or "").strip().lower().rstrip(" ?!.,;:")

    def _start_name(self, text):
        raw = str(text or "").strip()
        for pattern in self.START_PATTERNS:
            match = re.match(pattern, raw, flags=re.I)
            if match:
                return match.group(1).strip(" .:;\n\t")
        return None

    @staticmethod
    def _format_context(context):
        if not context.get("ok"):
            return f"Não consegui ler o contexto atual: {context.get('error', 'erro desconhecido')}"
        app = context.get("app_label") or context.get("app_id") or "aplicativo desconhecido"
        process_name = context.get("process_name") or "processo não identificado"
        title = context.get("window_title") or "sem título de janela"
        hint = context.get("document_hint") or ""
        lines = [
            f"Contexto atual: {app} (`{process_name}`).",
            f"Janela ativa: {title}.",
        ]
        if hint and hint != title:
            lines.append(f"Documento/projeto provável: {hint}.")
        return "\n".join(lines)

    @staticmethod
    def _format_recent(result):
        items = [x for x in result.get("items", []) if x.get("event_type") == "window_focus"]
        if not items:
            return (
                f"Ainda não há mudanças de contexto registradas nos últimos "
                f"{result.get('minutes', 30)} minutos."
            )
        lines = [f"Atividade recente ({result.get('minutes', 30)} min):"]
        for item in items[-12:]:
            payload = item.get("payload") or {}
            app = payload.get("app_label") or item.get("app_id") or "unknown"
            hint = payload.get("document_hint") or item.get("window_title") or ""
            when = str(item.get("ts") or "")
            if "T" in when:
                when = when.split("T", 1)[1][:8]
            lines.append(f"• {when or '--:--'} — {app}: {hint[:120]}")
        return "\n".join(lines)

    @staticmethod
    def _format_summary(result):
        if not result.get("ok"):
            return f"Não consegui resumir a atividade: {result.get('error', 'erro desconhecido')}"
        apps = result.get("apps") or {}
        transitions = result.get("transitions") or []
        lines = [
            f"Resumo dos últimos {result.get('minutes', 60)} minutos: "
            f"{result.get('events', 0)} eventos estruturais.",
        ]
        if apps:
            top = ", ".join(f"{name} ({count})" for name, count in list(apps.items())[:6])
            lines.append(f"Aplicativos mais observados: {top}.")
        if transitions:
            top_transitions = ", ".join(
                f"{x.get('from')} → {x.get('to')} ({x.get('count')})"
                for x in transitions[:5]
            )
            lines.append(f"Transições frequentes: {top_transitions}.")
        return "\n".join(lines)

    @staticmethod
    def _format_patterns(result):
        patterns = result.get("patterns") or []
        if not patterns:
            return (
                "Ainda não há repetição suficiente para afirmar um padrão de trabalho. "
                "Continue com o observador pessoal ativo; nenhuma automação será criada "
                "automaticamente nesta fase."
            )
        lines = ["Padrões de contexto repetidos que encontrei:"]
        for item in patterns[:8]:
            seq = " → ".join(item.get("sequence") or [])
            lines.append(f"• {seq} — {item.get('count', 0)} ocorrência(s)")
        lines.append(
            "Nesta fase esses padrões são apenas evidência; eles ainda não viram Skills "
            "automaticamente."
        )
        return "\n".join(lines)

    @staticmethod
    def _format_operational_context(result):
        if not result.get("ok"):
            return f"Não consegui montar o contexto operacional: {result.get('error', 'erro desconhecido')}"
        current = result.get("current") or {}
        episode = result.get("latest_episode") or {}
        expert = result.get("expert") or {}
        procedures = result.get("related_procedures") or []
        lines = [
            f"Contexto operacional: {current.get('app_label') or current.get('app_id') or 'desconhecido'}.",
            f"Janela atual: {current.get('window_title') or 'sem título'}.",
        ]
        if current.get("document_hint"):
            lines.append(f"Documento/projeto provável: {current.get('document_hint')}.")
        if episode:
            seq = " → ".join(episode.get("apps") or [])
            lines.append(
                f"Último episódio de trabalho: {seq or 'sem sequência identificável'} "
                f"({episode.get('events',0)} eventos)."
            )
            if episode.get("documents"):
                lines.append("Documentos recentes: " + "; ".join(episode.get("documents")[:5]) + ".")
        lines.append(
            f"Especialista deste app: {expert.get('maturity','unseen')} — "
            f"{expert.get('procedures',0)} procedimento(s) aprendido(s)."
        )
        if procedures:
            lines.append("Rotinas relacionadas que já conheço:")
            for item in procedures[:5]:
                lines.append(
                    f"• {item.get('name')} — {item.get('maturity')} — confiança "
                    f"{float(item.get('confidence') or 0):.0%}"
                )
        return "\n".join(lines)

    @staticmethod
    def _format_procedures(result):
        items = result.get("items") or []
        if not items:
            return "Ainda não há procedimentos persistidos na memória procedural. Ensine uma rotina com ‘observe enquanto eu faço ...’."
        lines = ["Memória procedural aprendida:"]
        for item in items[:15]:
            apps = ", ".join(item.get("app_ids") or []) or "app não identificado"
            lines.append(
                f"• {item.get('name')} — {item.get('maturity')} — "
                f"{item.get('step_count',0)} passos — apps: {apps} — "
                f"confiança {float(item.get('confidence') or 0):.0%}"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_experts(result):
        items = result.get("items") or []
        if not items:
            return "Ainda não observei aplicativos suficientes para formar perfis de experiência."
        lines = ["Experiência por aplicativo:"]
        for item in items[:15]:
            lines.append(
                f"• {item.get('app_id')} — {item.get('maturity')} — "
                f"{item.get('observed_events',0)} eventos — "
                f"{item.get('procedures',0)} procedimento(s)"
            )
        return "\n".join(lines)

    @staticmethod
    def _format_learning(result):
        if not result.get("ok"):
            return "Não consegui calcular o estado do aprendizado pessoal."
        observer = result.get("observer") or {}
        procedures = result.get("procedures") or {}
        experts = result.get("experts") or []
        patterns = result.get("patterns") or []
        learned_apps = [x for x in experts if x.get("maturity") in {"learned", "practiced"}]
        lines = [
            "Estado do aprendizado pessoal:",
            f"• Observador: {'ativo' if observer.get('active') else 'desativado'}",
            f"• Episódios de trabalho detectados: {result.get('episodes',0)}",
            f"• Aplicativos observados: {len(experts)}",
            f"• Aplicativos com aprendizado procedural: {len(learned_apps)}",
            f"• Procedimentos aprendidos: {procedures.get('procedures',0)}",
            f"• Procedimentos confiáveis/autônomos: "
            f"{procedures.get('trusted',0) + procedures.get('autonomous',0)}",
            f"• Padrões repetidos detectados: {len(patterns)}",
        ]
        lines.append(
            "A autonomia aumenta quando uma rotina é demonstrada, reutilizada com sucesso e recebe poucas correções."
        )
        return "\n".join(lines)

    def handle(self, text):
        raw = str(text or "").strip()
        low = self._clean(raw)

        # Existing explicit demonstration controls. Keep the old generic
        # "pare de observar" behavior when an explicit demonstration is active;
        # otherwise the same phrase stops the passive observer.
        if low == "pare de observar" and self.observe.active:
            self.observe.stop()
            self._name = None
            return {"handled": True, "ok": True, "answer": "Demonstração cancelada."}

        if any(self._clean(x) in low for x in self.CANCEL):
            if self.observe.active:
                self.observe.stop()
                self._name = None
                return {"handled": True, "ok": True, "answer": "Demonstração cancelada."}
            return {"handled": True, "ok": False, "answer": "Não há uma demonstração ativa."}

        if any(self._clean(x) in low for x in self.FINISH):
            if not self.observe.active:
                return {"handled": True, "ok": False, "answer": "Não há uma demonstração ativa."}
            session_id = self.observe.session_id
            stopped = self.observe.stop()
            if not stopped.get("ok"):
                return {
                    "handled": True,
                    "ok": False,
                    "answer": stopped.get("error", "Não consegui encerrar a demonstração."),
                }
            candidate = self.observe.build_candidate(session_id, name=self._name)
            if not candidate.get("ok"):
                return {
                    "handled": True,
                    "ok": False,
                    "answer": candidate.get("error", "Não consegui compilar a demonstração."),
                }
            data = candidate.get("candidate", {})
            saved = self.skills.save_parametric_skill(
                name=self._name or data.get("name") or f"demonstracao_{session_id}",
                steps=data.get("steps", []),
                inputs=data.get("inputs", {}),
                description=(
                    f"Skill aprendida por demonstração em {session_id}. "
                    "Conteúdo digitado foi mascarado por privacidade."
                ),
            )
            name = self._name or data.get("name") or f"demonstracao_{session_id}"
            self._name = None
            if not saved.get("ok"):
                return {
                    "handled": True,
                    "ok": False,
                    "answer": saved.get("error", "Não consegui salvar a skill demonstrada."),
                }
            inputs = list((data.get("inputs") or {}).keys())
            extra = (
                f" Entradas variáveis detectadas: {', '.join(inputs)}." if inputs else ""
            )
            procedure = self.observe.remember_procedure(
                name=name,
                source_session=session_id,
                skill_name=name,
                app_ids=data.get("apps") or [],
                inputs=data.get("inputs") or {},
                step_count=int(saved.get("steps", 0) or 0),
                metadata={"candidate_path": candidate.get("path", ""), "source": "human_demonstration"},
            )
            proc_data = procedure.get("procedure") or {}
            maturity = proc_data.get("maturity") or "learned"
            return {
                "handled": True,
                "ok": True,
                "answer": (
                    f"Aprendi por demonstração a skill “{name}” com "
                    f"{saved.get('steps', 0)} passo(s).{extra} "
                    f"Também registrei a rotina na memória procedural ({maturity})."
                ),
            }

        name = self._start_name(raw)
        if name:
            if self.observe.active:
                return {
                    "handled": True,
                    "ok": False,
                    "answer": "Já existe uma demonstração em andamento.",
                }
            result = self.observe.start(label=name)
            if not result.get("ok"):
                return {
                    "handled": True,
                    "ok": False,
                    "answer": result.get("error", "Não consegui iniciar a observação."),
                }
            self._name = name
            return {
                "handled": True,
                "ok": True,
                "answer": (
                    f"Estou observando para aprender “{name}”. Faça a rotina normalmente "
                    "no computador. Por privacidade, o texto digitado não é gravado; ele "
                    "vira uma entrada variável. Quando terminar, diga “terminei a demonstração”."
                ),
            }

        # Phase 1 personal observer controls.
        if low in {self._clean(x) for x in self.PASSIVE_START}:
            result = self.observe.start_passive()
            if not result.get("ok"):
                return {"handled": True, "ok": False, "answer": result.get("error", "Falha ao ativar o observador.")}
            return {
                "handled": True,
                "ok": True,
                "answer": (
                    "Observador pessoal ativado e persistente. A partir de agora registro "
                    "mudanças de aplicativo/janela e contexto estrutural em segundo plano. "
                    "Continuo sem gravar conteúdo digitado nem screenshots contínuos. "
                    "Você pode perguntar “o que estou fazendo agora?” ou “o que eu fiz nos "
                    "últimos 30 minutos?”."
                ),
            }

        if low in {self._clean(x) for x in self.PASSIVE_STOP} or low == "pare de observar":
            result = self.observe.stop_passive()
            return {
                "handled": True,
                "ok": bool(result.get("ok")),
                "answer": (
                    "Observador pessoal desativado. O histórico já salvo foi preservado."
                    if result.get("ok")
                    else result.get("error", "Falha ao desativar o observador.")
                ),
            }

        if low in {self._clean(x) for x in self.PASSIVE_STATUS}:
            result = self.observe.passive_status()
            state = "ativo" if result.get("active") else "desativado"
            return {
                "handled": True,
                "ok": True,
                "answer": (
                    f"Observador pessoal: {state}. Eventos persistidos: "
                    f"{result.get('events', 0)}. Intervalo: "
                    f"{result.get('interval_seconds', 2.0)} s."
                ),
            }

        if low in {self._clean(x) for x in self.CONTEXT_QUERIES}:
            return {
                "handled": True,
                "ok": True,
                "answer": self._format_context(self.observe.current_context(record=True)),
            }

        recent_match = re.match(
            r"^o que eu fiz nos (?:últimos|ultimos)\s+(\d+)\s+minutos$", low, flags=re.I
        )
        if recent_match:
            minutes = max(1, min(int(recent_match.group(1)), 24 * 60))
            result = self.observe.recent_activity(minutes=minutes, limit=200)
            return {"handled": True, "ok": True, "answer": self._format_recent(result)}

        summary_match = re.match(
            r"^(?:resuma|minha atividade|resuma minha atividade)(?: dos (?:últimos|ultimos)\s+(\d+)\s+minutos)?$",
            low,
            flags=re.I,
        )
        if summary_match:
            minutes = int(summary_match.group(1) or 60)
            result = self.observe.activity_summary(minutes=max(1, min(minutes, 24 * 60)))
            return {"handled": True, "ok": True, "answer": self._format_summary(result)}

        if low in {self._clean(x) for x in self.OPERATIONAL_CONTEXT_QUERIES}:
            result = self.observe.operational_context(minutes=180, max_procedures=6)
            return {"handled": True, "ok": True, "answer": self._format_operational_context(result)}

        if low in {self._clean(x) for x in self.PROCEDURE_QUERIES}:
            result = self.observe.list_procedures(limit=30)
            return {"handled": True, "ok": True, "answer": self._format_procedures(result)}

        search_proc = re.match(r"^(?:procure|busque|encontre) (?:uma )?(?:rotina|procedimento)(?: sobre| para)?\s+(.+)$", low, flags=re.I)
        if search_proc:
            result = self.observe.search_procedures(search_proc.group(1), limit=8)
            return {"handled": True, "ok": True, "answer": self._format_procedures(result)}

        expert_match = re.match(
            r"^(?:o que você sabe sobre|o que voce sabe sobre|status do especialista|especialista)\s+(.+)$",
            low,
            flags=re.I,
        )
        if expert_match:
            app_query = expert_match.group(1).strip()
            aliases = {
                "photoshop": "photoshop", "adobe photoshop": "photoshop",
                "vscode": "vscode", "visual studio code": "vscode",
                "visual studio": "visual_studio", "chrome": "chrome",
                "opera": "opera", "edge": "edge", "word": "word",
                "excel": "excel", "obs": "obs", "explorer": "explorer",
            }
            app_id = aliases.get(app_query, app_query.replace(" ", "_"))
            result = self.observe.app_expertise(app_id=app_id)
            return {
                "handled": True,
                "ok": True,
                "answer": (
                    f"{result.get('label', app_id)}: maturidade {result.get('maturity')}. "
                    f"Observei {result.get('observed_events',0)} eventos e tenho "
                    f"{result.get('procedures',0)} procedimento(s) aprendido(s).\n"
                    f"Estratégia preferida: {' → '.join(result.get('preferred_execution') or [])}.\n"
                    f"Bridge: {result.get('bridge','unknown')}."
                ),
            }

        if low in {self._clean(x) for x in self.EXPERT_QUERIES}:
            result = self.observe.app_expertise(limit=30)
            return {"handled": True, "ok": True, "answer": self._format_experts(result)}

        if low in {self._clean(x) for x in self.LEARNING_QUERIES}:
            result = self.observe.learning_snapshot()
            return {"handled": True, "ok": True, "answer": self._format_learning(result)}

        if low in {self._clean(x) for x in self.PATTERN_QUERIES}:
            result = self.observe.activity_patterns(minutes=8 * 60, min_count=2, limit=12)
            return {"handled": True, "ok": True, "answer": self._format_patterns(result)}

        return {"handled": False, "ok": True}

    def status(self):
        base = self.observe.status()
        return {**base, "teaching_name": self._name}
