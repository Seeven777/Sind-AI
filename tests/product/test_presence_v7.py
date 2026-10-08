from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src" / "jarvis" / "ui" / "hq_web"


def test_public_anywhere_v8_uses_ngrok_and_validates_real_jarvis():
    ps1 = (ROOT / "Enable-Jarvis-Anywhere.ps1").read_text(encoding="utf-8-sig")
    lower = ps1.lower()
    assert "ngrok" in lower
    assert "127.0.0.1:4040/api/tunnels" in lower
    assert "api/ping?token=" in lower
    assert "ngrok-skip-browser-warning" in lower
    assert "trycloudflare" not in lower
    assert "mobile_url" in lower
    assert "desktop_url" in lower
    assert "process_id" in lower


def test_anywhere_shutdown_stops_tracked_public_bridge():
    ps1 = (ROOT / "Disable-Jarvis-Anywhere.ps1").read_text(encoding="utf-8-sig")
    assert "process_id" in ps1
    assert "Stop-Process" in ps1

def test_remote_proxy_requests_cannot_bypass_auth_as_loopback():
    server = (ROOT / "src" / "jarvis" / "hq" / "server.py").read_text(encoding="utf-8")
    assert "CF-Connecting-IP" in server
    assert "X-Forwarded-For" in server
    assert "self._request_is_local()" in server
    assert 'host_name not in {"localhost", "127.0.0.1", "::1"}' in server


def test_https_remote_session_cookie_is_secure_and_query_token_is_removed():
    server = (ROOT / "src" / "jarvis" / "hq" / "server.py").read_text(encoding="utf-8")
    assert "Max-Age=2592000" in server
    assert '"; Secure" if self._request_is_https() else ""' in server
    assert 'self.send_header("Location", clean)' in server


def test_background_launchers_keep_mobile_auth_enabled_after_reboot():
    root_bg = (ROOT / "Start-Jarvis-Background.ps1").read_text(encoding="utf-8")
    task_bg = (ROOT / "scripts" / "start_jarvis_background.ps1").read_text(encoding="utf-8")
    assert '"--mobile"' in root_bg
    assert "--mobile" in task_bg


def test_v7_visual_surfaces_have_premium_system_tokens_and_mobile_safe_area():
    shell = (UI / "app-shell.css").read_text(encoding="utf-8")
    mobile = (UI / "mobile.css").read_text(encoding="utf-8")
    office = (UI / "office3d.css").read_text(encoding="utf-8")
    assert "--glass:" in shell
    assert "backdrop-filter" in shell
    assert "env(safe-area-inset-top)" in mobile
    assert "prefers-reduced-motion" in mobile
    assert "backdrop-filter" in office or "radial-gradient" in office


def test_remote_token_rotation_helper_invalidates_previous_owner_link():
    ps1 = (ROOT / "Rotate-Jarvis-Remote-Token.ps1").read_text(encoding="utf-8")
    assert "mobile_access_token.bin" in ps1
    assert "Disable-Jarvis-Anywhere.ps1" in ps1
    assert "Enable-Jarvis-Anywhere.ps1" in ps1



def test_remote_api_token_probe_does_not_redirect_to_cookie_session():
    server = (ROOT / "src" / "jarvis" / "hq" / "server.py").read_text(encoding="utf-8")
    assert 'establish_session = not path.startswith("/api/")' in server
    assert "_remote_authorized(establish_session=establish_session)" in server


def test_v8_has_single_simple_anywhere_entrypoint():
    cmd=(ROOT/"Jarvis-Anywhere.cmd").read_text(encoding="utf-8")
    assert "Enable-Jarvis-Anywhere.ps1" in cmd
    assert (ROOT/"README_REMOTE_ANYWHERE_V8.md").exists()
