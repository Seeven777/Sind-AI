import sys
import unittest

suite = unittest.defaultTestLoader.loadTestsFromName("tests.test_phase4_whatsapp_interactive")
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(0 if result.wasSuccessful() else 1)
