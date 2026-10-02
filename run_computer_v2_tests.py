from __future__ import annotations
import compileall
import sys
import unittest
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    ok = compileall.compile_dir(str(root), quiet=1)
    print("Compilação/sintaxe:", "OK" if ok else "FALHOU")
    if not ok:
        return 2

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    for name in (
        "tests.test_computer_runtime_v2",
        "tests.test_whatsapp_runtime_v2",
        "tests.test_phase4_whatsapp_interactive",
    ):
        suite.addTests(loader.loadTestsFromName(name))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
