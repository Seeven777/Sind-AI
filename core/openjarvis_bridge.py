"""Cliente local para usar o OpenJarvis oficial como núcleo conversacional."""

from __future__ import annotations

from typing import Any
import time

import requests


class OpenJarvisBridge:
    """Adaptador OpenAI-compatible com fallback controlado pelo chamador."""

    def __init__(self, config: dict[str, Any]):
        self.enabled = bool(config.get("openjarvis_enabled", True))
        self.base_url = str(
            config.get("openjarvis_base_url", "http://127.0.0.1:8000")
        ).rstrip("/")
        self.model = str(config.get("openjarvis_model", "qwen3.5:2b"))
        self.timeout = max(5, int(config.get("openjarvis_timeout_seconds", 180)))
        self._session = requests.Session()
        self._health_value = False
        self._health_checked_at = 0.0
        self._health_ttl = max(2.0, float(config.get("openjarvis_health_cache_seconds", 12)))

    def health(self) -> bool:
        if not self.enabled:
            return False
        now = time.monotonic()
        if now - self._health_checked_at < self._health_ttl:
            return self._health_value
        try:
            response = self._session.get(f"{self.base_url}/health", timeout=1.2)
            self._health_value = response.ok
        except requests.RequestException:
            self._health_value = False
        self._health_checked_at = now
        return self._health_value

    def chat(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Integração OpenJarvis desativada.")

        response = self._session.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 2048,
                "stream": False,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        choices = payload.get("choices") or []
        if not choices:
            raise RuntimeError("OpenJarvis respondeu sem alternativas.")
        content = ((choices[0].get("message") or {}).get("content") or "").strip()
        if not content:
            raise RuntimeError("OpenJarvis respondeu sem conteúdo.")
        return {
            "message": {"role": "assistant", "content": content},
            "_jarvis_model": payload.get("model") or self.model,
            "_openjarvis": True,
            "usage": payload.get("usage") or {},
        }
