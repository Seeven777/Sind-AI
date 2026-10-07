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


def test_voice_service_exposes_browser_fallback_when_unconfigured(monkeypatch):
    for key in (
        "JARVIS_ELEVENLABS_API_KEY", "JARVIS_ELEVENLABS_VOICE_ID",
        "JARVIS_PIPER", "JARVIS_PIPER_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)
    voice = VoiceService()
    health = voice.health()
    assert health["tts"]["status"] == "unconfigured"
    assert health["tts_backends"]["browser_fallback"]["status"] == "available"
