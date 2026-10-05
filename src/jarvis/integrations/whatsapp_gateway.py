from __future__ import annotations

import json
import urllib.error
import urllib.request


class WhatsAppGatewayError(RuntimeError):
    pass


class WhatsAppGatewayClient:
    """Optional WA-AKG REST bridge.

    WA-AKG is kept as a separate transport. The default Jarvis WhatsApp tool
    continues using the Desktop controller until gateway delivery verification
    has been explicitly integrated and validated.
    """

    provider_id = "wa-akg"

    def __init__(
        self,
        *,
        base_url: str = "",
        api_key: str = "",
        session_id: str = "",
        timeout_seconds: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session_id = session_id
        self.timeout_seconds = max(5, int(timeout_seconds))

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.session_id)

    def health(self) -> dict:
        if not self.configured:
            return {
                "status": "unconfigured",
                "provider": self.provider_id,
                "base_url": self.base_url or None,
                "session_id": self.session_id or None,
            }

        try:
            raw = self._request(f"/api/sessions/{self.session_id}", method="GET")
            return {
                "status": "healthy",
                "provider": self.provider_id,
                "session_id": self.session_id,
                "session": raw,
            }
        except Exception as exc:
            return {
                "status": "unavailable",
                "provider": self.provider_id,
                "session_id": self.session_id,
                "error": str(exc),
            }

    def _request(self, path: str, *, method: str, payload: dict | None = None):
        if not self.configured:
            raise WhatsAppGatewayError("WA-AKG não está configurado.")

        data = None
        headers = {
            "Accept": "application/json",
            "X-API-Key": self.api_key,
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
            raise WhatsAppGatewayError(
                f"WA-AKG HTTP {exc.code}: {detail}"
            ) from exc
        except Exception as exc:
            raise WhatsAppGatewayError(f"WA-AKG indisponível: {exc}") from exc

    def send_text(self, jid: str, message: str) -> dict:
        if not jid or not message:
            raise WhatsAppGatewayError("jid e mensagem são obrigatórios.")
        return self._request(
            f"/api/messages/{self.session_id}/{jid}/send",
            method="POST",
            payload={"message": {"text": message}},
        )

    def list_session_chats(self) -> dict:
        return self._request(
            f"/api/chat/{self.session_id}",
            method="GET",
        )
