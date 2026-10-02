from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def ok(label: str) -> None:
    print(f"[OK] {label}")


def fail(label: str, detail: str) -> None:
    print(f"[FAIL] {label}: {detail}")
    raise SystemExit(1)


def main() -> int:
    py_files = [
        ROOT / "app.py",
        ROOT / "jarvis_desktop.py",
        ROOT / "run_integrated_jarvis.py",
        ROOT / "runtime" / "local_secrets.py",
        ROOT / "scripts" / "jarvis_elevenlabs_tts.py",
        ROOT / "scripts" / "configure_elevenlabs_voice.py",
        ROOT / "scripts" / "cleanup_project.py",
    ]
    for path in py_files:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except Exception as exc:
            fail(f"Python {path.name}", str(exc))
    ok("Sintaxe Python")

    try:
        json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    except Exception as exc:
        fail("vercel.json", str(exc))
    ok("vercel.json válido")

    node = shutil_which("node")
    if node:
        proc = subprocess.run([node, "--check", str(ROOT / "ui" / "web" / "orb.js")], capture_output=True, text=True)
        if proc.returncode:
            fail("orb.js", proc.stderr.strip())
        ok("Sintaxe JavaScript")
    else:
        print("[SKIP] Node não disponível; orb.js não validado pelo Node.")

    css = (ROOT / "ui" / "web" / "jarvis-cinematic-v2.css").read_text(encoding="utf-8")
    if css.count("{") != css.count("}"):
        fail("CSS", "chaves desbalanceadas")
    ok("Estrutura CSS")

    print("\nOverlay pronto para ser copiado sobre o repositório Sind-AI.")
    return 0


def shutil_which(name: str):
    import shutil
    return shutil.which(name)


if __name__ == "__main__":
    raise SystemExit(main())
