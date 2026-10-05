from __future__ import annotations

import asyncio

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import MockModelProvider


def test_product_runtime_registers_ai_mesh_and_nemotron(monkeypatch, tmp_path):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("JARVIS_PRIVACY_MODE", "hybrid")
    rt = asyncio.run(start_product_runtime(tmp_path, model_provider=MockModelProvider()))
    try:
        assert rt.ai_mesh.hermes.provider_id == "hermes"
        assert rt.ai_mesh.whatsapp_gateway.provider_id == "wa-akg"
        assert rt.ai_mesh.creative.provider_id == "open-generative-ai"
        assert rt.model_registry.get("nvidia_nemotron").provider_id == "nvidia_nemotron"
        assert rt.model_router.premium_provider == "nvidia_nemotron"
        assert rt.model_router.privacy_mode == "hybrid"
    finally:
        asyncio.run(rt.close())
