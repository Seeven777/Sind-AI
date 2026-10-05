from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


class CreativeStudioError(RuntimeError):
    pass


class CreativeStudioClient:
    """Open Generative AI / Muapi-compatible creative backend client.

    The upstream studio uses a submit -> poll pattern with ``x-api-key`` and
    model-specific endpoints under ``/api/v1``. This client remains transport-
    neutral so Jarvis can drive image/video/audio/lipsync endpoints configured
    by the caller without hard-coding a model catalog.
    """

    provider_id = "open-generative-ai"

    def __init__(
        self,
        *,
        base_url: str = "https://api.muapi.ai",
        api_key: str = "",
        timeout_seconds: int = 60,
        poll_seconds: int = 3,
        max_polls: int = 100,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = max(5, int(timeout_seconds))
        self.poll_seconds = max(1, int(poll_seconds))
        self.max_polls = max(1, int(max_polls))

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def health(self) -> dict:
        return {
            "status": "configured" if self.configured else "unconfigured",
            "provider": self.provider_id,
            "base_url": self.base_url,
        }

    def _request(self, path: str, *, method: str, payload=None):
        if not self.configured:
            raise CreativeStudioError("Creative Studio não está configurado.")

        data = None
        headers = {
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise CreativeStudioError(
                f"Creative API HTTP {exc.code}: {detail}"
            ) from exc
        except Exception as exc:
            raise CreativeStudioError(f"Creative API indisponível: {exc}") from exc

    def submit(self, endpoint: str, parameters: dict) -> dict:
        if not endpoint:
            raise CreativeStudioError("Endpoint criativo obrigatório.")
        return self._request(
            f"/api/v1/{endpoint.lstrip('/')}",
            method="POST",
            payload=parameters,
        )

    def poll(self, request_id: str) -> dict:
        if not request_id:
            raise CreativeStudioError("request_id obrigatório.")
        return self._request(
            f"/api/v1/predictions/{request_id}/result",
            method="GET",
        )

    @staticmethod
    def _request_id(payload: dict) -> str | None:
        prediction = payload.get("prediction") or {}
        value = (
            payload.get("request_id")
            or payload.get("id")
            or prediction.get("request_id")
            or prediction.get("id")
        )
        return str(value) if value else None

    @staticmethod
    def normalize_result(payload: dict) -> dict:
        """Normalize common Muapi result shapes into a stable Jarvis result."""
        result = dict(payload or {})
        outputs = result.get("outputs")
        output_url = result.get("url")
        if not output_url and isinstance(outputs, list) and outputs:
            first = outputs[0]
            if isinstance(first, str):
                output_url = first
            elif isinstance(first, dict):
                output_url = first.get("url") or first.get("output")
        if output_url:
            result["url"] = output_url
        return result

    def generate(
        self,
        endpoint: str,
        parameters: dict,
        *,
        wait: bool = True,
    ) -> dict:
        submitted = self.submit(endpoint, parameters)
        request_id = self._request_id(submitted)
        if not wait or not request_id:
            return {"submitted": submitted, "request_id": request_id}

        for _ in range(self.max_polls):
            result = self.normalize_result(self.poll(request_id))
            status = str(result.get("status") or "").lower()
            if status in {"completed", "succeeded", "success"}:
                if not result.get("url") and not result.get("outputs"):
                    raise CreativeStudioError(
                        f"Job {request_id} terminou sem output verificável."
                    )
                return {
                    "request_id": request_id,
                    "status": status,
                    "result": result,
                }
            if status in {"failed", "error", "cancelled", "canceled"}:
                raise CreativeStudioError(
                    f"Job criativo terminou em estado {status}: {result}"
                )
            time.sleep(self.poll_seconds)

        raise CreativeStudioError(
            f"Job {request_id} não terminou dentro do limite de polling."
        )
