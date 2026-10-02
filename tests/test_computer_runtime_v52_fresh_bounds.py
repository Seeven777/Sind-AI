import unittest

from runtime.phase4.whatsapp_uia import (
    _hit_chain_is_whatsapp_surface,
    _point_inside_bounds,
)


class FreshBoundsLogicTests(unittest.TestCase):
    def test_generic_webview_owned_by_whatsapp_is_valid_surface(self):
        hit = {
            "chain": [
                {
                    "name": "",
                    "automation_id": "WebView",
                    "control_type": "Pane",
                },
                {
                    "name": "WhatsApp",
                    "automation_id": "",
                    "control_type": "Window",
                },
            ]
        }
        self.assertTrue(_hit_chain_is_whatsapp_surface(hit))

    def test_foreign_window_rejects_surface(self):
        hit = {
            "chain": [
                {
                    "name": "",
                    "automation_id": "WebView",
                    "control_type": "Pane",
                },
                {
                    "name": "Windows PowerShell",
                    "automation_id": "",
                    "control_type": "Window",
                },
            ]
        }
        self.assertFalse(_hit_chain_is_whatsapp_surface(hit))

    def test_point_must_be_inside_fresh_bounds(self):
        self.assertTrue(_point_inside_bounds((1300, 360), [1200, 330, 1450, 410], 2))
        self.assertFalse(_point_inside_bounds((1500, 360), [1200, 330, 1450, 410], 2))


if __name__ == "__main__":
    unittest.main()
