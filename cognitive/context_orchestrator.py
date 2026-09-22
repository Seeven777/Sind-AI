class ContextOrchestrator:
    """Monta contexto pequeno, relevante e hierarquizado para modelos locais."""

    def __init__(self, conversations, learning, memory, semantic, projects, attachments, services=None):
        self.conversations = conversations
        self.learning = learning
        self.memory = memory
        self.semantic = semantic
        self.projects = projects
        self.attachments = attachments
        self.services = services

    def build(self, query, max_chars=4200):
        parts = []
        budget = int(max_chars)

        project = self.projects.context(query, max_chars=min(1100, budget))
        if project.get("text"):
            parts.append(project["text"])

        if self.services:
            try:
                sr = self.services.context(query, limit=4)
            except Exception:
                sr = {"items":[]}
            if sr.get("items"):
                lines = []
                for item in sr["items"]:
                    lines.append(
                        f"- {item.get('name')} ({item.get('kind')}): {item.get('url')} | "
                        f"acesso={item.get('access')} | {item.get('notes','')}"
                    )
                parts.append("SERVIÇOS INSTITUCIONAIS RELEVANTES:\n" + "\n".join(lines))

        pid = self.projects.current_id()
        sid = self.conversations.current_session_id
        attach = self.attachments.search_context(
            query, session_id=sid, project_id=pid, limit=4, max_chars=min(1500, budget)
        )
        if attach.get("text"):
            parts.append("ANEXOS RELEVANTES:\n" + attach["text"])

        lessons = self.learning.relevant(query, limit=4)
        if lessons:
            parts.append(
                "LIÇÕES/PREFERÊNCIAS:\n" +
                "\n".join(f"- {x.get('lesson')}" for x in lessons if x.get("lesson"))
            )

        try:
            memories = self.memory.relevant(query, limit=4)
        except Exception:
            memories = []
        if memories:
            parts.append(
                "MEMÓRIAS:\n" +
                "\n".join(f"- {x.get('value')}" for x in memories if x.get("value"))
            )

        if getattr(self.semantic, "enabled", False):
            try:
                sem = self.semantic.search(query, limit=3)
            except Exception:
                sem = {"items":[]}
            if sem.get("items"):
                parts.append(
                    "MEMÓRIA SEMÂNTICA:\n" +
                    "\n".join(f"- {x.get('text','')[:700]}" for x in sem["items"])
                )

        # Recent/relevant conversation is kept last so it survives truncation.
        messages = self.conversations.context_messages(
            query, recent_limit=5, relevant_limit=3, max_chars=1800
        )
        conversation_text = []
        for m in messages:
            role = "Usuário" if m.get("role") == "user" else "Jarvis"
            conversation_text.append(f"{role}: {m.get('content','')}")
        if conversation_text:
            parts.append("CONVERSA RELEVANTE:\n" + "\n".join(conversation_text))

        text = "\n\n".join(x for x in parts if x.strip())
        if len(text) > budget:
            text = text[-budget:]
        return {
            "ok": True,
            "text": text,
            "project": project.get("project"),
            "attachments": attach.get("items", []),
            "messages": messages,
        }
