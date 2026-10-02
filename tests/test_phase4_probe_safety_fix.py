import unittest

from runtime.phase4.controls import choose_text_field
from runtime.phase4.whatsapp_uia import choose_window_candidate


def field(key, name, **extra):
    return {
        "key": key,
        "name": name,
        "automation_id": "",
        "control_type": "Edit",
        "visible": True,
        "enabled": True,
        "read_only": False,
        "password": False,
        "bounds": [100, 100, 400, 140],
        **extra,
    }


class SafetyRegressionTests(unittest.TestCase):
    def test_transparent_webview_without_uia_evidence_is_rejected(self):
        rows = [{
            "hwnd": 1,
            "pid": 20,
            "exe": "msedgewebview2.exe",
            "title": "",
            "class_name": "Chrome_WidgetWin_1",
            "visible": True,
            "alpha_zero": True,
            "foreground": False,
            "bounds": [0, 0, 1920, 1080],
        }]
        self.assertIsNone(choose_window_candidate(rows))

    def test_real_alpha_zero_webview_with_rich_uia_is_accepted(self):
        rows = [{
            "hwnd": 133056,
            "pid": 2828,
            "exe": "msedgewebview2.exe",
            "title": "WhatsApp",
            "class_name": "Chrome_WidgetWin_1",
            "visible": False,
            "alpha_zero": True,
            "foreground": False,
            "bounds": [1150, 94, 1884, 923],
            "uia_ok": True,
            "accessibility_score": 1860,
        }]
        self.assertEqual(choose_window_candidate(rows)["hwnd"], 133056)

    def test_ambiguous_composer_still_fails_closed(self):
        with self.assertRaises(RuntimeError):
            choose_text_field(
                [
                    field("composer1", "Digite uma mensagem"),
                    field("composer2", "Digite uma mensagem"),
                ],
                purpose="message",
            )


if __name__ == "__main__":
    unittest.main()
