import re
from urllib.parse import urlsplit


class ConversationalAnswerEngine:
    """Conversa normal e Q&A institucional antes do Agent Runtime pesado."""

    def __init__(self, model_router, conversations, learning, institutional,
                 institutional_knowledge, web_search):
        self.models = model_router
        self.conversations = conversations
        self.learning = learning
        self.institutional = institutional
        self.institutional_knowledge = institutional_knowledge
        self.web_search = web_search

    def _looks_like_question(self, text):
        t = str(text or "").strip().lower()
        return (
            "?" in t
            or t.startswith((
                "quem ", "o que ", "oque ", "qual ", "quais ", "como ",
                "onde ", "quando ", "por que ", "porque ", "me explique",
                "explique", "fale sobre", "conte sobre"
            ))
        )

    def _institutional_topic(self, text):
        t = str(text or "").lower()
        return any(x in t for x in (
            "sindpetshop", "sind petshop", "sindpetshop-sp",
            "nosso sindicato", "o sindicato", "nossa cct",
            "convenção coletiva", "convencao coletiva"
        ))

    def should_handle(self, text, selected_tools=None):
        if not selected_tools:
            return True
        if self._institutional_topic(text) and self._looks_like_question(text):
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
            result = self.web_search.search(
                f"site:sindpetshop.org.br {query}",
                limit=4
            )
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

    def _deterministic_fallback(self, grounded):
        profile = grounded.get("profile") or {}
        if profile:
            values = []
            for key in ("name","nome","organization_name","description","descricao",
                        "mission","missao","representation","representacao"):
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

        web = grounded.get("web") or []
        if web:
            first = web[0]
            snippet = re.sub(r"\s+", " ", first.get("snippet","")).strip()
            domain = urlsplit(first.get("url","")).netloc
            if snippet:
                return (
                    f"Segundo a fonte pública {domain}, {snippet[:1000]}\n\n"
                    f"Fonte: {first.get('url','')}"
                )

        return (
            "Ainda não tenho informação suficiente nas bases locais para responder isso com segurança. "
            "Posso pesquisar fontes públicas e incorporar o resultado à nossa base."
        )

    def answer(self, user_text):
        grounded = {"text":"", "profile":{}, "evidence":[], "web":[]}
        if self._institutional_topic(user_text):
            grounded = self._institutional_context(user_text)

        recent = self.conversations.context_messages(
            user_text, recent_limit=4, relevant_limit=3, max_chars=2200
        )
        lessons = self.learning.relevant(user_text, limit=3)
        lesson_text = "\n".join(
            f"- {x.get('lesson')}" for x in lessons if x.get("lesson")
        )

        system = (
            "Você é Jarvis, um GPT pessoal local. Responda naturalmente em português. "
            "Não mencione Actions, Workflows ou infraestrutura técnica sem pedido. "
            "Se houver evidência abaixo, use-a para os fatos e não invente lacunas."
        )
        if lesson_text:
            system += "\n\nPreferências/correções relevantes:\n" + lesson_text
        if grounded.get("text"):
            system += "\n\nEVIDÊNCIA PARA ESTA RESPOSTA:\n" + grounded["text"]

        messages = [{"role":"system","content":system}] + recent[-5:] + [
            {"role":"user","content":user_text}
        ]

        try:
            response = self.models.chat(
                messages=messages,
                user_text=user_text,
                force="fast",
            )
            content = ((response.get("message") or {}).get("content") or "").strip()
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.I|re.S).strip()
            if content:
                return {
                    "ok": True,
                    "answer": content,
                    "model": response.get("_jarvis_model"),
                    "grounded": bool(grounded.get("text")),
                    "fallback": False,
                }
        except Exception as exc:
            return {
                "ok": True,
                "answer": self._deterministic_fallback(grounded),
                "model": None,
                "grounded": bool(grounded.get("text")),
                "fallback": True,
                "error": str(exc),
            }

        return {
            "ok": True,
            "answer": self._deterministic_fallback(grounded),
            "model": None,
            "grounded": bool(grounded.get("text")),
            "fallback": True,
        }
