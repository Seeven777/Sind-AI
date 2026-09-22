import json
import tempfile
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
        "mobile_companion_port": 18970,
        "persistent_root_name": "JarvisMobileHotfixTest",
    }

    mobile = MobileCompanion(Dummy(), cfg, base)
    state = mobile.start()
    check("Mobile starts", state.get("ok") and state.get("running"), state)

    url = f"http://127.0.0.1:{mobile.port}/"
    with urllib.request.urlopen(url, timeout=3) as r:
        body = r.read().decode("utf-8")
    check("Root serves HTML", "Jarvis Mobile" in body, body[:200])

    with urllib.request.urlopen(url + "health", timeout=3) as r:
        health = json.loads(r.read().decode("utf-8"))
    check("Health route", health.get("ok") and health.get("index_exists"), health)

    req = urllib.request.Request(url + "favicon.ico")
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            code = r.status
    except urllib.error.HTTPError as exc:
        code = exc.code
    check("favicon no 404", code != 404, code)

    mobile.stop()
    print("\\nMobile Hotfix test concluído.")


if __name__ == "__main__":
    main()
