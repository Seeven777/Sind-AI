import unittest

from runtime.phase4.whatsapp_uia import choose_whatsapp_shell


class ForegroundOwnershipTests(unittest.TestCase):
    def test_root_shell_beats_webview_renderer(self):
        rows = [
            {
                "hwnd": 133056,
                "pid": 2828,
                "exe": "msedgewebview2.exe",
                "title": "WhatsApp",
                "class_name": "Chrome_WidgetWin_1",
                "foreground": False,
                "alpha_zero": True,
                "bounds": [1150,94,1884,923],
            },
            {
                "hwnd": 133020,
                "pid": 16492,
                "exe": "whatsapp.root.exe",
                "title": "WhatsApp",
                "class_name": "WinUIDesktopWin32WindowClass",
                "foreground": False,
                "alpha_zero": False,
                "bounds": [1142,93,1892,931],
            },
        ]
        chosen = choose_whatsapp_shell(rows)
        self.assertEqual(chosen["hwnd"], 133020)

    def test_tiny_helper_is_not_shell(self):
        rows = [{
            "hwnd": 1,
            "pid": 16492,
            "exe": "whatsapp.root.exe",
            "title": "WhatsApp",
            "class_name": "WinUIDesktopWin32WindowClass",
            "foreground": False,
            "alpha_zero": False,
            "bounds": [0,0,1,1],
        }]
        self.assertIsNone(choose_whatsapp_shell(rows))


if __name__ == "__main__":
    unittest.main()
