import re
from urllib.parse import urlsplit


class ConversationalAnswerEngine:
    """
    Conversa leve e grounded antes do Agent Runtime.

    Não substitui o agente: quando há ferramentas/execução real, o Agent Runtime
    continua responsável. Aqui tratamos diálogo, contexto e perguntas factuais
    leves sem transformar tudo em Task.
    """

    def __init__(
        self, model_router, conversations, learning, institutional,
        institutional_knowledge, web_search, context_orchestrator=None,
        public_data=None
    ):
        self.models = model_router
        self.conversations = conversations
        self.learning = learning
        self.institutional = institutional
        self.institutional_knowledge = institutional_knowledge
        self.web_search = web_search
        self.context_orchestrator = context_orchestrator
        self.public_data = public_data

    def _looks_like_question(self, text):
        t = str(text or "").strip().lower()
        return (
            "?" in t
            or t.startswith((
                "quem ", "o que ", "oque ", "qual ", "quais ", "como ",
                "onde ", "quando ", "por que ", "porque ", "me explique",
                "explique", "fale sobre", "conte sobre", "você sabe", "voce sabe"
            ))
        )

    def _institutional_topic(self, text):
        t = str(text or "").lower()
        return any(x in t for x in (
            "sindpetshop", "sind petshop", "sindpetshop-sp",
            "nosso sindicato", "o sindicato", "nossa cct",
            "convenção coletiva", "convencao coletiva"
        ))

    def _fresh_topic(self, text):
        t = str(text or "").lower()
        markers = (
            "hoje", "agora", "atual", "atualmente", "mais recente", "último",
            "ultimo", "nova regra", "mudou", "notícia", "noticia", "2026",
            "preço atual", "cotação", "cotacao"
        )
        return self._looks_like_question(text) and any(x in t for x in markers)

    def should_handle(self, text, selected_tools=None):
        # Conversa sem ferramentas candidatas é sempre leve.
        if not selected_tools:
            return True
        # Pergunta institucional é respondida com grounding específico.
        if self._institutional_topic(text) and self._looks_like_question(text):
            return True
        # Questões atuais explícitas podem usar pesquisa leve em vez de um Agent job.
        if self._fresh_topic(text):
            return True
        return False

    def _institutional_context(self, query):
        profile = self.institutional.execute("profile_get")
        profile_data = profile.get("data", {}) if profile.get("ok") else {}

        evidence = self.institutional_knowledge.execute(
            "evidence_pack", query=query, limit=5, max_chars=2600
        )
        evidence_items = evidence.get("items", []) if evidence.get("ok") else []

        web_items = []
        if not profile_data and not evidence_items:
            result = self.web_search.search(f"site:sindpetshop.org.br {query}", limit=4)
            if result.get("ok"):
                web_items = result.get("items", [])[:4]

        chunks = []
        if profile_data:
            compact = [f"{k}: {v}" for k, v in profile_data.items() if str(v).strip()]
            if compact:
                chunks.append("PERFIL INSTITUCIONAL:\n" + "\n".join(compact[:25]))

        if evidence_items:
            lines = []
            for item in evidence_items:
                lines.append(
                    f"{item.get('citation','')} {item.get('title','')}\n"
                    f"{item.get('text','')[:900]}"
                )
            chunks.append("EVIDÊNCIAS INTERNAS:\n" + "\n\n".join(lines))

        if web_items:
            lines = []
            for item in web_items:
                lines.append(
                    f"Título: {item.get('title','')}\n"
                    f"URL: {item.get('url','')}\n"
                    f"Trecho: {item.get('snippet','')[:700]}"
                )
            chunks.append("FONTES PÚBLICAS:\n" + "\n\n".join(lines))

        return {
            "profile": profile_data,
            "evidence": evidence_items,
            "web": web_items,
            "text": "\n\n".join(chunks)[:4200],
        }

    def _fresh_web_context(self, query):
        result = self.web_search.search(query, limit=5)
        items = result.get("items", [])[:5] if result.get("ok") else []
        lines = []
        for item in items:
            lines.append(
                f"Título: {item.get('title','')}\n"
                f"URL: {item.get('url','')}\n"
                f"Trecho: {item.get('snippet','')[:650]}"
            )
        return {"items": items, "text": "\n\n".join(lines)[:3400]}

    def _public_source_context(self, query):
        if not self.public_data:
            return {"items": [], "text": ""}
        try:
            r = self.public_data.recommend(query, limit=5)
        except Exception:
            return {"items": [], "text": ""}
        items = r.get("items", [])
        if not items:
            return {"items": [], "text": ""}
        lines = []
        for x in items:
            lines.append(
                f"- {x.get('name')} [{x.get('authority','')}] — "
                f"{x.get('notes','')} | acesso: {x.get('access','')}"
            )
        return {"items": items, "text": "\n".join(lines)[:1800]}

    def _deterministic_fallback(self, grounded, web=None):
        profile = grounded.get("profile") or {}
        if profile:
            values = []
            for key in (
                "name","nome","organization_name","description","descricao",
                "mission","missao","representation","representacao"
            ):
                value = profile.get(key)
                if value and value not in values:
                    values.append(str(value))
            if values:
                return " ".join(values[:4])

        evidence = grounded.get("evidence") or []
        if evidence:
            item = evidence[0]
            excerpt = re.sub(r"\s+", " ", item.get("text","")).strip()
            return f"Segundo {item.get('title') or 'o material institucional'}, {excerpt[:950]}"

        public_items = (web or {}).get("items", []) or grounded.get("web", [])
        if public_items:
            first = public_items[0]
            snippet = re.sub(r"\s+", " ", first.get("snippet","")).strip()
            domain = urlsplit(first.get("url","")).netloc
            if snippet:
                return (
                    f"Segundo a fonte pública {domain}, {snippet[:1000]}\n\n"
                    f"Fonte: {first.get('url','')}"
                )

        return (
            "Não tenho contexto suficiente para afirmar isso com segurança. "
            "Posso pesquisar fontes públicas ou você pode anexar material para eu usar como base."
        )

    def answer(self, user_text):
        grounded = {"text":"", "profile":{}, "evidence":[], "web":[]}
        if self._institutional_topic(user_text):
            grounded = self._institutional_context(user_text)

        orchestrated = {"text":"", "messages":[]}
        if self.context_orchestrator:
            try:
                orchestrated = self.context_orchestrator.build(user_text, max_chars=3600)
            except Exception:
                pass

        fresh = {"text":"", "items":[]}
        if self._fresh_topic(user_text) and not grounded.get("text"):
            fresh = self._fresh_web_context(user_text)

        source_hint = {"text":"", "items":[]}
        if any(x in user_text.lower() for x in (
            "dados", "estatística", "estatistica", "população", "populacao",
            "emprego", "economia", "cnpj", "processos", "município", "municipio"
        )):
            source_hint = self._public_source_context(user_text)

        lessons = self.learning.relevant(user_text, limit=3)
        lesson_text = "\n".join(
            f"- {x.get('lesson')}" for x in lessons if x.get("lesson")
        )

        system = (
            "Você é Jarvis, um GPT pessoal local. Responda naturalmente em português, "
            "com continuidade de conversa. Não mencione infraestrutura técnica sem necessidade. "
            "Não invente fatos ausentes. Quando houver fontes/evidências, use-as e deixe claro "
            "quando algo é apenas sugestão ou inferência. "
            "Nunca exponha chain-of-thought, análise interna ou tags <think>. "
            "Jarvis Mobile é somente uma interface remota do Jarvis executando no computador host; "
            "se o usuário estiver no celular, não afirme que controla aplicativos do telefone. "
            "Ações de desktop continuam acontecendo no computador host."
        )
        if lesson_text:
            system += "\n\nPREFERÊNCIAS/CORREÇÕES:\n" + lesson_text
        if orchestrated.get("text"):
            system += "\n\nCONTEXTO PESSOAL/PROJETO:\n" + orchestrated["text"]
        if grounded.get("text"):
            system += "\n\nEVIDÊNCIA INSTITUCIONAL:\n" + grounded["text"]
        if fresh.get("text"):
            system += "\n\nFONTES PÚBLICAS RECENTES:\n" + fresh["text"]
        if source_hint.get("text"):
            system += "\n\nFONTES ESTRUTURADAS DISPONÍVEIS (não trate como dados já consultados):\n" + source_hint["text"]

        messages = [{"role":"system","content":system}]
        for m in (orchestrated.get("messages") or [])[-5:]:
            messages.append({"role":m.get("role","user"), "content":m.get("content","")})
        messages.append({"role":"user","content":user_text})

        try:
            response = self.models.chat(messages=messages, user_text=user_text, force="fast")
            content = ((response.get("message") or {}).get("content") or "").strip()
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.I|re.S).strip()
            if content:
                return {
                    "ok": True,
                    "answer": content,
                    "model": response.get("_jarvis_model"),
                    "grounded": bool(grounded.get("text") or fresh.get("text")),
                    "fallback": False,
                    "sources": fresh.get("items") or grounded.get("web") or [],
                }
        except Exception as exc:
            return {
                "ok": True,
                "answer": self._deterministic_fallback(grounded, fresh),
                "model": None,
                "grounded": bool(grounded.get("text") or fresh.get("text")),
                "fallback": True,
                "error": str(exc),
                "sources": fresh.get("items") or grounded.get("web") or [],
            }

        return {
            "ok": True,
            "answer": self._deterministic_fallback(grounded, fresh),
            "model": None,
            "grounded": bool(grounded.get("text") or fresh.get("text")),
            "fallback": True,
            "sources": fresh.get("items") or grounded.get("web") or [],
        }
