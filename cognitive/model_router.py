import re


class AdaptiveModelRouter:
    """
    Seleciona modelos locais já instalados em vez de presumir hardware/modelo fixo.

    FAST   -> menor modelo conversacional adequado disponível.
    REASON -> modelo configurado ou o maior modelo conversacional local disponível.

    Modelos de embedding são ignorados para chat.
    """

    def __init__(
        self,
        ollama,
        fast_model="qwen3:1.7b",
        reasoning_model="qwen3:4b",
        fast_timeout=18,
        reasoning_timeout=40,
        fallback_timeout=22,
    ):
        self.ollama = ollama
        self.fast_model = fast_model
        self.reasoning_model = reasoning_model
        self.fast_timeout = int(fast_timeout)
        self.reasoning_timeout = int(reasoning_timeout)
        self.fallback_timeout = int(fallback_timeout)

    def _chat_models(self):
        models = self.ollama.list_models()
        blocked = ("embed", "nomic", "bge-", "mxbai")
        return [m for m in models if not any(x in m.lower() for x in blocked)]

    def _size_score(self, model):
        m = re.search(r":(\d+(?:\.\d+)?)b(?:-|$)", str(model).lower())
        if m:
            return float(m.group(1))
        # Unknown sizes stay in the middle instead of being discarded.
        return 3.0

    def fast_model_name(self):
        installed = self._chat_models()
        if self.fast_model in installed:
            return self.fast_model
        if not installed:
            return self.fast_model
        # Favor small models for latency.
        return sorted(installed, key=lambda x: (self._size_score(x), x))[0]

    def reason_model_name(self):
        installed = self._chat_models()
        if self.reasoning_model in installed:
            return self.reasoning_model
        if not installed:
            return self.reasoning_model
        # Favor the strongest model that is already installed.
        return sorted(installed, key=lambda x: (self._size_score(x), x), reverse=True)[0]

    def status(self):
        installed = self.ollama.list_models()
        fast = self.fast_model_name()
        reason = self.reason_model_name()
        return {
            "ok": True,
            "installed": installed,
            "requested_fast_model": self.fast_model,
            "fast_model": fast,
            "fast_available": fast in installed,
            "requested_reasoning_model": self.reasoning_model,
            "reasoning_model": reason,
            "reasoning_available": reason in installed,
            "single_model_mode": bool(fast == reason),
        }

    def is_complex(self, text, tools=None):
        if tools:
            return True
        t = str(text or "").lower()
        if len(t) > 900:
            return True
        markers = (
            "analise profundamente", "compare detalhadamente", "planeje",
            "implemente", "corrija o código", "corrija o codigo",
            "crie um sistema", "automatize", "investigue",
            "faça uma pesquisa completa", "faca uma pesquisa completa",
            "pesquisa completa", "múltiplas etapas", "multiplas etapas",
        )
        return any(x in t for x in markers)

    def chat(self, messages, user_text="", tools=None, force=None):
        mode = force or ("reason" if self.is_complex(user_text, tools) else "fast")

        if mode == "reason":
            model = self.reason_model_name()
            return self.ollama.chat(
                messages=messages,
                tools=tools,
                timeout=self.reasoning_timeout,
                model=model,
            )

        fast = self.fast_model_name()
        installed = self._chat_models()
        if fast in installed:
            return self.ollama.chat(
                messages=messages,
                timeout=self.fast_timeout,
                model=fast,
                num_ctx=4096,
                temperature=0.2,
            )

        reason = self.reason_model_name()
        return self.ollama.chat(
            messages=messages,
            timeout=self.fallback_timeout,
            model=reason,
            num_ctx=3072,
            temperature=0.2,
        )
