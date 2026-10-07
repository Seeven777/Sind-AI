from pathlib import Path

from jarvis.voice import VoiceService


def test_companion_v2_is_minimal_presence():
    root = Path(__file__).resolve().parents[2] / "src" / "jarvis" / "ui" / "hq_web"
    html = (root / "companion.html").read_text(encoding="utf-8")
    js = (root / "companion.js").read_text(encoding="utf-8")
    assert 'id="open-sidebar"' in html
    assert 'id="jarvis-core"' in html
    assert 'id="input"' in html
    assert 'class="drawer"' in html
    assert 'context-panel' not in html
    assert '/surface-engine.js' not in html
    assert "'voice.replies':true" in js
    assert "/api/voice/synthesize" in js


def test_voice_service_exposes_browser_fallback_when_cloud_and_piper_are_unconfigured(monkeypatch):
    for key in (
        "JARVIS_ELEVENLABS_API_KEY", "JARVIS_ELEVENLABS_VOICE_ID",
        "JARVIS_PIPER", "JARVIS_PIPER_MODEL",
        "JARVIS_CHATTERBOX_URL", "JARVIS_TTS_PROVIDER",
    ):
        monkeypatch.delenv(key, raising=False)

    voice = VoiceService()
    health = voice.health()

    # Presence v6 adds Edge Neural TTS as the preferred zero-config voice when
    # installed. Windows SAPI remains the final local fallback; on platforms
    # without either, browser Web Speech remains available.
    edge = health["tts_backends"]["edge_tts"]
    windows = health["tts_backends"]["windows_sapi"]
    if edge["status"] == "healthy":
        assert health["tts"]["status"] == "healthy"
        assert health["tts"]["backend"] == "edge-tts"
    elif windows["status"] == "healthy":
        assert health["tts"]["status"] == "healthy"
        assert health["tts"]["backend"] == "windows-sapi"
    else:
        assert health["tts"]["status"] == "unconfigured"

    assert health["tts_backends"]["browser_fallback"]["status"] == "available"
