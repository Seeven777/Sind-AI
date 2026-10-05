from __future__ import annotations

from typing import Sequence

from .base import ChatMessage, ModelResponse, ModelUnavailableError
from .openai_compatible import OpenAICompatibleProvider


class NvidiaNemotronProvider(OpenAICompatibleProvider):
    """NVIDIA Nemotron 3 Ultra provider over an OpenAI-compatible endpoint."""

    provider_id = "nvidia_nemotron"

    def __init__(
        self,
        base_url: str = "https://integrate.api.nvidia.com/v1",
        api_key: str = "",
        default_model: str = "nvidia/nemotron-3-ultra-550b-a55b",
        *,
        timeout: int = 180,
        enable_thinking: bool = True,
        max_tokens: int = 16384,
        thinking_token_budget: int | None = None,
    ):
        super().__init__(
            self.provider_id,
            base_url,
            api_key,
            default_model,
            timeout=timeout,
        )
        self.enable_thinking = bool(enable_thinking)
        self.max_tokens = max(256, int(max_tokens))
        self.thinking_token_budget = (
            None if thinking_token_budget is None else max(128, int(thinking_token_budget))
        )

    def health(self) -> dict:
        if not self.api_key:
            return {
                "status": "unconfigured",
                "provider": self.provider_id,
                "base_url": self.base_url,
                "default_model": self.default_model,
            }
        return super().health()

    def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        model: str | None = None,
        system: str | None = None,
    ) -> ModelResponse:
        wire = []
        if system:
            wire.append({"role": "system", "content": system})
        wire.extend({"role": m.role, "content": m.content} for m in messages)

        selected = model or self.default_model
        request = {
            "model": selected,
            "messages": wire,
            "stream": False,
            "temperature": 1.0,
            "top_p": 0.95,
            "max_tokens": self.max_tokens,
            "chat_template_kwargs": {
                "enable_thinking": self.enable_thinking,
                "force_nonempty_content": True,
            },
        }
        if self.thinking_token_budget is not None:
            # NVIDIA's Nemotron 3 Ultra examples expose the reasoning ceiling
            # as the top-level ``reasoning_budget`` field.
            request["reasoning_budget"] = self.thinking_token_budget

        raw = self._request("/chat/completions", request)
        choices = raw.get("choices") or []
        if not choices:
            raise ModelUnavailableError(
                f"{self.provider_id} retornou zero choices."
            )
        message = choices[0].get("message") or {}
        content = str(message.get("content") or "").strip()
        if not content:
            raise ModelUnavailableError(
                f"{self.provider_id} retornou conteúdo final vazio."
            )
        return ModelResponse(
            content,
            selected,
            self.provider_id,
            {
                "usage": raw.get("usage"),
                "finish_reason": choices[0].get("finish_reason"),
                "thinking_enabled": self.enable_thinking,
                "thinking_token_budget": self.thinking_token_budget,
            },
        )

    def probe(self, model: str | None = None) -> dict:
        selected = model or self.default_model
        try:
            response = self.chat(
                [ChatMessage("user", "Responda somente com OK.")],
                model=selected,
                system="Responda de forma curta.",
            )
            return {
                "status": "healthy",
                "provider": self.provider_id,
                "model": response.model,
                "content": response.content,
                "metadata": response.metadata,
            }
        except Exception as exc:
            return {
                "status": "failed",
                "provider": self.provider_id,
                "model": selected,
                "error": str(exc),
            }
