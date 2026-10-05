from __future__ import annotations

import asyncio
import os
import stat

from jarvis.integrations import (
    CreativeStudioClient,
    HermesAgentBridge,
    WhatsAppGatewayClient,
)
from jarvis.models import ChatMessage, NvidiaNemotronProvider
from pathlib import Path


def test_nemotron_provider_uses_documented_request_shape():
    provider = NvidiaNemotronProvider(api_key="test", enable_thinking=False, thinking_token_budget=512)
    captured = {}

    def fake_request(path, payload):
        captured["path"] = path
        captured["payload"] = payload
        return {
            "choices": [{
                "message": {"content": "OK"},
                "finish_reason": "stop",
            }],
            "usage": {"total_tokens": 3},
        }

    provider._request = fake_request
    response = provider.chat([ChatMessage("user", "teste")])

    assert response.content == "OK"
    assert captured["path"] == "/chat/completions"
    payload = captured["payload"]
    assert payload["model"] == "nvidia/nemotron-3-ultra-550b-a55b"
    assert payload["chat_template_kwargs"] == {
        "enable_thinking": False,
        "force_nonempty_content": True,
    }
    assert payload["reasoning_budget"] == 512
    assert payload["stream"] is False
    assert "extra_body" not in payload


def test_nemotron_provider_probe_unconfigured_is_explicit():
    provider = NvidiaNemotronProvider(api_key="")
    result = provider.health()
    assert result["status"] == "unconfigured"
    assert result["provider"] == "nvidia_nemotron"


def test_hermes_bridge_uses_safe_one_shot_mode(tmp_path, monkeypatch):
    exe = tmp_path / "hermes"
    exe.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "print('ARGS=' + ' '.join(sys.argv[1:]))\n"
        "print('HERMES_OK')\n",
        encoding="utf-8",
    )
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(tmp_path) + os.pathsep + os.environ.get("PATH", ""))

    bridge = HermesAgentBridge(profile="jarvis", toolsets="safe", timeout_seconds=10)
    assert bridge.health()["status"] == "healthy"
    result = asyncio.run(bridge.run("Faça uma análise"))
    assert result.success is True
    assert "HERMES_OK" in result.content
    assert "--profile jarvis" in result.content
    assert "-z Faça uma análise" in result.content
    assert "--toolsets safe" in result.content


def test_whatsapp_gateway_uses_documented_send_route():
    client = WhatsAppGatewayClient(
        base_url="http://gateway",
        api_key="secret",
        session_id="session_01",
    )
    captured = {}

    def fake_request(path, *, method, payload=None):
        captured.update(path=path, method=method, payload=payload)
        return {"id": "msg-1"}

    client._request = fake_request
    result = client.send_text("5511999999999@s.whatsapp.net", "Olá")
    assert result["id"] == "msg-1"
    assert captured == {
        "path": "/api/messages/session_01/5511999999999@s.whatsapp.net/send",
        "method": "POST",
        "payload": {"message": {"text": "Olá"}},
    }


def test_creative_client_normalizes_output_and_polling():
    client = CreativeStudioClient(api_key="secret", poll_seconds=0, max_polls=3)
    calls = []

    def fake_request(path, *, method, payload=None):
        calls.append((path, method, payload))
        if method == "POST":
            return {"request_id": "req-1"}
        return {"status": "completed", "outputs": [{"url": "https://cdn.example/out.mp4"}]}

    client._request = fake_request
    result = client.generate("video-test", {"prompt": "teste"})
    assert result["request_id"] == "req-1"
    assert result["result"]["url"] == "https://cdn.example/out.mp4"
    assert calls[0] == ("/api/v1/video-test", "POST", {"prompt": "teste"})
    assert calls[1][0] == "/api/v1/predictions/req-1/result"


def test_hermes_bridge_resolves_extensionless_path_entry_on_windows(tmp_path, monkeypatch):
    exe = tmp_path / "hermes"
    exe.write_text("#!/usr/bin/env python3\nprint('shim')\n", encoding="utf-8")
    exe.chmod(exe.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setenv("PATH", str(tmp_path))

    bridge = HermesAgentBridge(profile="", toolsets="safe")
    assert Path(bridge.executable()).resolve() == exe.resolve()
