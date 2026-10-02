import unittest

suite = unittest.defaultTestLoader.discover('tests', pattern='test_phase4_intent_regression.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
