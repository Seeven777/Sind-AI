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
        "JARVIS_TTS_PROVIDER",
    ):
        monkeypatch.delenv(key, raising=False)

    voice = VoiceService()
    health = voice.health()

    # On Windows, Presence v4 intentionally promotes the native SAPI engine to
    # the active zero-config backend. On other platforms the active backend may
    # remain unconfigured and the browser Web Speech fallback is used. Both are
    # valid states; what must always remain available is a spoken fallback.
    windows = health["tts_backends"]["windows_sapi"]
    if windows["status"] == "healthy":
        assert health["tts"]["status"] == "healthy"
        assert health["tts"]["backend"] == "windows-sapi"
    else:
        assert health["tts"]["status"] == "unconfigured"

    assert health["tts_backends"]["browser_fallback"]["status"] == "available"
