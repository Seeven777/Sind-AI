class AdaptiveModelRouter:
    """FAST para conversa. REASON para ferramentas e trabalho complexo."""

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

    def status(self):
        installed = self.ollama.list_models()
        return {
            "ok": True,
            "installed": installed,
            "fast_model": self.fast_model,
            "fast_available": self.ollama.has_model(self.fast_model),
            "reasoning_model": self.reasoning_model,
            "reasoning_available": self.ollama.has_model(self.reasoning_model),
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
        )
        return any(x in t for x in markers)

    def chat(self, messages, user_text="", tools=None, force=None):
        mode = force or ("reason" if self.is_complex(user_text, tools) else "fast")
        if mode == "reason":
            return self.ollama.chat(
                messages=messages,
                tools=tools,
                timeout=self.reasoning_timeout,
                model=self.reasoning_model,
            )

        if self.ollama.has_model(self.fast_model):
            return self.ollama.chat(
                messages=messages,
                timeout=self.fast_timeout,
                model=self.fast_model,
                num_ctx=4096,
                temperature=0.2,
            )

        # Fallback curto: uma pergunta simples não pode congelar 40s só porque
        # o modelo FAST ainda não foi instalado.
        return self.ollama.chat(
            messages=messages,
            timeout=self.fallback_timeout,
            model=self.reasoning_model,
            num_ctx=3072,
            temperature=0.2,
        )
