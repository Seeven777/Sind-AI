from __future__ import annotations
import compileall
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def main():
    if not compileall.compile_dir(str(ROOT), quiet=1):
        print("Falha de compilação/sintaxe.")
        return 2
    print("Compilação/sintaxe: OK")
    modules = [
        "tests.test_computer_runtime_v4_hit_test",
        "tests.test_whatsapp_raw_bridge_v3",
        "tests.test_computer_runtime_v2",
        "tests.test_whatsapp_runtime_v2",
        "tests.test_phase4_whatsapp_interactive",
    ]
    return subprocess.run(
        [sys.executable, "-m", "unittest", *modules, "-v"],
        cwd=str(ROOT),
    ).returncode

if __name__ == "__main__":
    raise SystemExit(main())
