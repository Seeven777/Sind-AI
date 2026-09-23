"""Run Phase 1 + Phase 2 personal-autonomy tests without pytest."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

suite = unittest.TestSuite()
for pattern in (
    "test_personal_observer.py",
    "test_personal_autonomy_phase2.py",
    "test_phase2_core_patcher.py",
):
    suite.addTests(unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern=pattern))
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
