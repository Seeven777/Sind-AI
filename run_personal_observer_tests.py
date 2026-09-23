"""Run Phase 1 tests without adding pytest as a dependency."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_personal_observer.py")
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
