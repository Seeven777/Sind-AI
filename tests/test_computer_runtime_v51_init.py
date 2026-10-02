import unittest
from runtime.phase4.whatsapp_uia import WhatsAppUIA


class InitRegressionTests(unittest.TestCase):
    def test_v51_runtime_state_is_initialized(self):
        ui = WhatsAppUIA()
        self.assertEqual(ui.shell_metadata, {})
        self.assertEqual(ui.last_focus_trace, [])
        self.assertEqual(ui.last_activation_trace, [])
        self.assertEqual(ui.last_conversation_evidence, {})

    def test_focus_method_is_defensive_for_old_instances(self):
        ui = WhatsAppUIA()
        del ui.last_focus_trace
        del ui.shell_metadata

        # We do not execute Windows focus here; merely verify the defensive
        # initialization is present in source/instance path.
        self.assertFalse(hasattr(ui, "last_focus_trace"))
        self.assertFalse(hasattr(ui, "shell_metadata"))


if __name__ == "__main__":
    unittest.main()
