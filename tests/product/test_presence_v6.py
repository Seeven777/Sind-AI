from pathlib import Path
import json

from jarvis.voice import EdgeNeuralTTS, ChatterboxTTS, VoiceService

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src" / "jarvis" / "ui" / "hq_web"


def test_edge_neural_defaults_to_male_brazilian_profile(monkeypatch):
    monkeypatch.delenv("JARVIS_EDGE_VOICE", raising=False)
    monkeypatch.delenv("JARVIS_EDGE_RATE", raising=False)
    monkeypatch.delenv("JARVIS_EDGE_PITCH", raising=False)
    voice = EdgeNeuralTTS()
    assert voice.voice == "pt-BR-AntonioNeural"
    assert voice.rate == "-6%"
    assert voice.pitch == "-14Hz"


def test_auto_voice_priority_prefers_chatterbox_then_edge(monkeypatch):
    monkeypatch.setenv("JARVIS_CHATTERBOX_URL", "http://127.0.0.1:4123")
    monkeypatch.delenv("JARVIS_TTS_PROVIDER", raising=False)
    service = VoiceService()
    order = [item.health()["backend"] for item in service._candidate_order()]
    assert order[:2] == ["chatterbox", "edge-tts"]


def test_chatterbox_adapter_is_optional_and_local(monkeypatch):
    monkeypatch.delenv("JARVIS_CHATTERBOX_URL", raising=False)
    assert ChatterboxTTS().health()["status"] == "unconfigured"
    configured = ChatterboxTTS(base_url="http://127.0.0.1:4123")
    health = configured.health()
    assert health["status"] == "healthy"
    assert health["url"] == "http://127.0.0.1:4123"


def test_dedicated_mobile_surface_is_present_and_uses_same_jarvis_apis():
    html = (UI / "mobile.html").read_text(encoding="utf-8")
    js = (UI / "mobile.js").read_text(encoding="utf-8")
    assert 'id="jarvis-core"' in html
    assert 'id="input"' in html
    assert "/api/chat" in js
    assert "/api/conversations" in js
    assert "/api/attention" in js
    assert "/api/voice/synthesize" in js
    assert "SpeechRecognition" in js or "webkitSpeechRecognition" in js
    assert "HTTPS" in js


def test_mobile_manifest_and_worker_include_mobile_shell():
    manifest = json.loads((UI / "mobile.webmanifest").read_text(encoding="utf-8"))
    sw = (UI / "sw.js").read_text(encoding="utf-8")
    assert manifest["start_url"] == "/mobile"
    assert "/mobile" in sw
    assert "/mobile.js" in sw
    assert "/mobile.css" in sw


def test_server_exposes_mobile_route_and_mobile_link():
    server = (ROOT / "src" / "jarvis" / "hq" / "server.py").read_text(encoding="utf-8")
    assert 'path == "/mobile"' in server
    assert '"/mobile?token="' in server or "/mobile?token=" in server


def test_companion_audio_has_subtle_presence_processing():
    js = (UI / "companion.js").read_text(encoding="utf-8")
    assert "createHighpass" in js or "highpass" in js
    assert "delay.delayTime.value=.008" in js


def test_voice_extra_installs_edge_tts():
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'edge-tts>=7.2.8,<8' in pyproject


def test_secure_mobile_helper_uses_tailnet_https():
    ps1 = (ROOT / "Enable-Jarvis-Mobile-Secure.ps1").read_text(encoding="utf-8")
    assert "tailscale" in ps1.lower()
    assert "serve" in ps1.lower()
    assert "https://" in ps1.lower()
