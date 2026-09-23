import re


class DemonstrationTeacher:
    """Ponte natural entre ObservationEngine e SkillStore."""

    START_PATTERNS = (
        r"^observe enquanto eu faço\s+(.+)$",
        r"^observe enquanto eu faco\s+(.+)$",
        r"^aprenda observando(?: como)?\s+(.+)$",
        r"^vou te mostrar(?: como)?\s+(.+)$",
        r"^quero te mostrar(?: como)?\s+(.+)$",
    )
    FINISH = (
        "terminei a demonstração", "terminei a demonstracao", "finalizar demonstração",
        "finalizar demonstracao", "fim da demonstração", "fim da demonstracao",
    )
    CANCEL = ("cancelar demonstração", "cancelar demonstracao", "pare de observar")

    def __init__(self, observe_engine, skill_store):
        self.observe = observe_engine
        self.skills = skill_store
        self._name = None

    def _start_name(self, text):
        raw = str(text or "").strip()
        for pattern in self.START_PATTERNS:
            m = re.match(pattern, raw, flags=re.I)
            if m:
                return m.group(1).strip(" .:;\n\t")
        return None

    def handle(self, text):
        raw = str(text or "").strip()
        low = raw.lower()

        if any(x in low for x in self.CANCEL):
            if self.observe.active:
                self.observe.stop()
            self._name = None
            return {"handled": True, "ok": True, "answer": "Demonstração cancelada."}

        if any(x in low for x in self.FINISH):
            if not self.observe.active:
                return {"handled": True, "ok": False, "answer": "Não há uma demonstração ativa."}
            session_id = self.observe.session_id
            stopped = self.observe.stop()
            if not stopped.get("ok"):
                return {"handled": True, "ok": False, "answer": stopped.get("error", "Não consegui encerrar a demonstração.")}
            candidate = self.observe.build_candidate(session_id, name=self._name)
            if not candidate.get("ok"):
                return {"handled": True, "ok": False, "answer": candidate.get("error", "Não consegui compilar a demonstração.")}
            data = candidate.get("candidate", {})
            saved = self.skills.save_parametric_skill(
                name=self._name or data.get("name") or f"demonstracao_{session_id}",
                steps=data.get("steps", []),
                inputs=data.get("inputs", {}),
                description=f"Skill aprendida por demonstração em {session_id}. Conteúdo digitado foi mascarado por privacidade.",
            )
            name = self._name or data.get("name") or f"demonstracao_{session_id}"
            self._name = None
            if not saved.get("ok"):
                return {"handled": True, "ok": False, "answer": saved.get("error", "Não consegui salvar a skill demonstrada.")}
            inputs = list((data.get("inputs") or {}).keys())
            extra = f" Entradas variáveis detectadas: {', '.join(inputs)}." if inputs else ""
            return {
                "handled": True, "ok": True,
                "answer": f"Aprendi por demonstração a skill “{name}” com {saved.get('steps',0)} passo(s).{extra}",
            }

        name = self._start_name(raw)
        if name:
            if self.observe.active:
                return {"handled": True, "ok": False, "answer": "Já existe uma demonstração em andamento."}
            result = self.observe.start(label=name)
            if not result.get("ok"):
                return {"handled": True, "ok": False, "answer": result.get("error", "Não consegui iniciar a observação.")}
            self._name = name
            return {
                "handled": True, "ok": True,
                "answer": (
                    f"Estou observando para aprender “{name}”. Faça a rotina normalmente no computador. "
                    "Por privacidade, o texto digitado não é gravado; ele vira uma entrada variável. "
                    "Quando terminar, diga “terminei a demonstração”."
                ),
            }

        return {"handled": False, "ok": True}

    def status(self):
        base = self.observe.status()
        return {**base, "teaching_name": self._name}
