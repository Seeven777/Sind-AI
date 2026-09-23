import json
import urllib.request
from pathlib import Path

from mobile.companion import MobileCompanion


class Dummy:
    pass


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    print("[OK]", name)


def main():
    base = Path(__file__).resolve().parent
    cfg = {
        "mobile_companion_host": "127.0.0.1",
        "mobile_companion_port": 19070,
        "persistent_root_name": "JarvisMobileRouteTest",
    }
    mobile = MobileCompanion(Dummy(), cfg, base)
    state = mobile.start()
    check("server starts", state.get("running"), state)

    base_url = f"http://127.0.0.1:{mobile.port}"

    with urllib.request.urlopen(base_url + "/", timeout=3) as r:
        root_html = r.read().decode("utf-8")
    check("root HTML", "Jarvis Mobile" in root_html, root_html[:200])

    # Exact failure reported by the user: PIN appended to URL.
    with urllib.request.urlopen(base_url + "/791327", timeout=3) as r:
        pin_html = r.read().decode("utf-8")
        status = r.status
    check("/791327 is not 404", status == 200, status)
    check("/791327 serves mobile UI", "Jarvis Mobile" in pin_html, pin_html[:200])

    with urllib.request.urlopen(base_url + "/health", timeout=3) as r:
        health = json.loads(r.read().decode("utf-8"))
    check("health", health.get("ok") and health.get("index_exists"), health)

    mobile.stop()
    print("\\nMobile route regression test concluído.")


if __name__ == "__main__":
    main()
