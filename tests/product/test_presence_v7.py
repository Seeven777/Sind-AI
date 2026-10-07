from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "src" / "jarvis" / "ui" / "hq_web"


def test_public_anywhere_launcher_uses_tailscale_funnel():
    ps1 = (ROOT / "Enable-Jarvis-Anywhere.ps1").read_text(encoding="utf-8")
    assert "tailscale funnel --bg" in ps1.lower()
    assert "mobile_url" in ps1
    assert "desktop_url" in ps1
    assert "token=" in ps1


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
