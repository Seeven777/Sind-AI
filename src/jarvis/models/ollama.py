from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Sequence

from .base import ChatMessage, ModelResponse, ModelUnavailableError


class OllamaProvider:
    provider_id = "ollama"

    def __init__(
        self,
        base_url,
        default_model,
        *,
        timeout_seconds=180,
        context_tokens=8192,
        temperature=.25,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout_seconds = timeout_seconds
        self.context_tokens = context_tokens
        self.temperature = temperature
        self._show_cache: dict[str, dict] = {}

    def _request(self, path, payload=None):
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(self.base_url + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                detail = str(exc)
            raise ModelUnavailableError(
                f"Ollama respondeu HTTP {exc.code} em {path}: {detail}"
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise ModelUnavailableError(
                f"Ollama indisponível em {self.base_url}: {exc}"
            ) from exc

    def list_models(self):
        raw = self._request("/api/tags")
        out = []
        for item in raw.get("models", []):
            name = item.get("name") or item.get("model")
            if name:
                out.append(str(name))
        return out

    def show_model(self, model: str | None = None) -> dict:
        selected = model or self.default_model
        if selected not in self._show_cache:
            try:
                self._show_cache[selected] = self._request(
                    "/api/show", {"model": selected}
                )
            except ModelUnavailableError:
                # Older Ollama builds may not expose the metadata we need.
                self._show_cache[selected] = {}
        return self._show_cache[selected]

    def health(self):
        try:
            models = self.list_models()
            metadata = self.show_model(self.default_model) if self.default_model in models else {}
            return {
                "status": "healthy",
                "provider": self.provider_id,
                "url": self.base_url,
                "models": models,
                "default_model_present": self.default_model in models,
                "thinking": metadata.get("thinking"),
                "capabilities": metadata.get("capabilities", []),
            }
        except ModelUnavailableError as exc:
            return {
                "status": "unavailable",
                "provider": self.provider_id,
                "url": self.base_url,
                "error": str(exc),
            }

    @staticmethod
    def _extract_content(raw: dict) -> tuple[str, str]:
        message = raw.get("message") or {}
        content = str(message.get("content") or "").strip()
        thinking = str(message.get("thinking") or "").strip()
        return content, thinking

    def _chat_payload(self, selected, wire, *, num_predict, think_value):
        payload = {
            "model": selected,
            "messages": wire,
            "stream": False,
            "options": {
                "num_ctx": self.context_tokens,
                "temperature": self.temperature,
                "num_predict": num_predict,
            },
        }
        if think_value is not None:
            payload["think"] = think_value
        return payload

    def _should_disable_thinking(self, selected: str) -> bool:
        metadata = self.show_model(selected)
        thinking = metadata.get("thinking")
        values = thinking.get("values", []) if isinstance(thinking, dict) else []
        if False in values:
            return True
        # Qwen 3.x/3.5 frequently defaults to reasoning. Native /api/chat supports
        # think:false on official models and avoids responses that exhaust the
        # output budget inside the reasoning channel.
        return selected.lower().startswith("qwen3")

    def chat(self, messages: Sequence[ChatMessage], *, model=None, system=None):
        selected = model or self.default_model
        wire = []
        if system:
            wire.append({"role": "system", "content": system})
        wire += [{"role": m.role, "content": m.content} for m in messages]

        disable_thinking = self._should_disable_thinking(selected)
        first_think = False if disable_thinking else None
        payload = self._chat_payload(
            selected, wire, num_predict=1024, think_value=first_think
        )

        try:
            raw = self._request("/api/chat", payload)
        except ModelUnavailableError as exc:
            # Some non-thinking/community models reject the think parameter.
            if first_think is False and "thinking" in str(exc).lower():
                payload.pop("think", None)
                raw = self._request("/api/chat", payload)
            else:
                raise

        content, thinking = self._extract_content(raw)
        retried = False

        if not content:
            # Controlled recovery for reasoning-capable models that return HTTP
            # 200 but place everything in message.thinking and no final answer.
            # We never expose the private reasoning trace as the answer.
            retry_payload = self._chat_payload(
                selected, wire, num_predict=2048, think_value=False
            )
            retry_payload["options"]["temperature"] = min(self.temperature, 0.2)
            try:
                retry_raw = self._request("/api/chat", retry_payload)
                retry_content, retry_thinking = self._extract_content(retry_raw)
                retried = True
                if retry_content:
                    raw, content, thinking = retry_raw, retry_content, retry_thinking
            except ModelUnavailableError as retry_exc:
                # Preserve the first successful HTTP response context below; the
                # caller receives a model-level failure, not an invented answer.
                if "thinking" not in str(retry_exc).lower():
                    raise

        if not content:
            done_reason = raw.get("done_reason")
            eval_count = raw.get("eval_count")
            thinking_chars = len(thinking)
            raise ModelUnavailableError(
                "Ollama concluiu a geração sem resposta final "
                f"usando {selected} (done_reason={done_reason!r}, "
                f"eval_count={eval_count!r}, thinking_chars={thinking_chars}, "
                f"retry={retried})."
            )

        metadata = {
            key: raw.get(key)
            for key in (
                "done_reason", "total_duration", "load_duration",
                "prompt_eval_count", "eval_count"
            )
        }
        metadata.update({
            "thinking_present": bool(thinking),
            "thinking_chars": len(thinking),
            "retried_for_empty_content": retried,
            "think_disabled": disable_thinking,
        })
        return ModelResponse(
            content,
            str(raw.get("model") or selected),
            self.provider_id,
            metadata,
        )

    def probe(self, model: str | None = None) -> dict:
        selected = model or self.default_model
        try:
            response = self.chat(
                [ChatMessage("user", "Responda somente com a palavra OK.")],
                model=selected,
                system="Responda de forma curta, sem explicações.",
            )
            return {
                "status": "healthy",
                "provider": self.provider_id,
                "model": response.model,
                "content": response.content,
                "metadata": response.metadata,
            }
        except ModelUnavailableError as exc:
            return {
                "status": "failed",
                "provider": self.provider_id,
                "model": selected,
                "error": str(exc),
            }
