import unittest

from runtime.phase4.whatsapp_uia import choose_window_candidate


class WindowDiscoveryRegressionTests(unittest.TestCase):
    def test_winui_root_can_win_even_when_reported_invisible(self):
        rows = [
            {
                "hwnd": 133020,
                "pid": 16492,
                "exe": "whatsapp.root.exe",
                "title": "WhatsApp",
                "class_name": "WinUIDesktopWin32WindowClass",
                "visible": False,
                "foreground": False,
                "alpha_zero": False,
                "bounds": [1142, 93, 1892, 931],
                "uia_ok": True,
                "uia_descendants": 300,
                "uia_fields": 2,
                "accessibility_score": 1200,
            },
            {
                "hwnd": 133056,
                "pid": 2828,
                "exe": "msedgewebview2.exe",
                "title": "WhatsApp",
                "class_name": "Chrome_WidgetWin_1",
                "visible": False,
                "foreground": False,
                "alpha_zero": True,
                "bounds": [1150, 94, 1884, 923],
                "uia_ok": True,
                "uia_descendants": 80,
                "uia_fields": 1,
                "accessibility_score": 500,
            },
        ]
        self.assertEqual(choose_window_candidate(rows)["hwnd"], 133020)

    def test_alpha_zero_webview_is_not_automatically_rejected(self):
        rows = [{
            "hwnd": 133056,
            "pid": 2828,
            "exe": "msedgewebview2.exe",
            "title": "WhatsApp",
            "class_name": "Chrome_WidgetWin_1",
            "visible": False,
            "foreground": False,
            "alpha_zero": True,
            "bounds": [1150, 94, 1884, 923],
            "uia_ok": True,
            "accessibility_score": 700,
        }]
        self.assertEqual(choose_window_candidate(rows)["hwnd"], 133056)

    def test_helper_windows_are_rejected(self):
        rows = [{
            "hwnd": 1,
            "pid": 16492,
            "exe": "whatsapp.root.exe",
            "title": "Default IME",
            "class_name": "IME",
            "visible": False,
            "foreground": False,
            "alpha_zero": False,
            "bounds": [0, 0, 500, 500],
            "uia_ok": True,
            "accessibility_score": 9999,
        }]
        self.assertIsNone(choose_window_candidate(rows))


if __name__ == "__main__":
    unittest.main()
