from pathlib import Path

from jarvis.brain.intent import IntentRouter
from jarvis.hq.server import _is_loopback, _mobile_access_token
from jarvis.models.router import ModelRouter


ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src" / "jarvis" / "ui" / "hq_web"


class _MemorySecrets:
    def __init__(self):
        self.values = {}

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


class _Runtime:
    def __init__(self):
        self.secret_store = _MemorySecrets()


def test_live_web_requests_route_to_research():
    router = IntentRouter()
    assert router.classify("Quais são as últimas notícias de hoje?").name == "research"
    assert router.classify("Veja a previsão do tempo hoje").name == "research"
    assert router.classify("Pesquise na internet avanços recentes em robótica").name == "research"


def test_role_models_have_truthful_fallbacks():
    router = ModelRouter(
        "ollama", "qwen3.5:4b",
        local_models={"general": "qwen3.5:4b", "fast": "llama3.2:1b", "coding": "qwen2.5-coder:3b"},
    )
    assert router.local_model("fast") == "llama3.2:1b"
    assert router.local_model("coding") == "qwen2.5-coder:3b"
    assert router.local_model("creative") == "qwen3.5:4b"
    assert router.route(capability="coding", privacy="local").model == "qwen2.5-coder:3b"


def test_office_monitors_face_the_agents():
    js = (UI / "office3d.js").read_text(encoding="utf-8")
    assert "screen.position.set(x,y,z+.043)" in js
    assert "screen.position.set(x,y,z-.043)" not in js


def test_voice_chain_confirms_browser_start_before_native_fallback():
    js = (UI / "companion.js").read_text(encoding="utf-8")
    assert "if(await speakWithBrowser(text,token,messageElement))return;" in js
    assert "if(await speakWithNativeWindows(text,token,messageElement))return;" in js
    assert js.index("if(await speakWithBrowser(text,token,messageElement))return;") < js.index(
        "if(await speakWithNativeWindows(text,token,messageElement))return;"
    )
    assert "u.onstart=()=>" in js
    assert "location.hostname" in js


def test_mobile_token_is_stable_and_loopback_remains_frictionless():
    runtime = _Runtime()
    first = _mobile_access_token(runtime)
    second = _mobile_access_token(runtime)
    assert first == second
    assert len(first) >= 32
    assert _is_loopback("127.0.0.1")
    assert _is_loopback("::1")
    assert not _is_loopback("192.168.1.10")


def test_standard_launcher_enables_protected_mobile_mode():
    launcher = (ROOT / "Start-Jarvis-UI.ps1").read_text(encoding="utf-8")
    assert '"--mobile"' in launcher
    html = (UI / "companion.html").read_text(encoding="utf-8")
    assert 'id="mobile-link"' in html
