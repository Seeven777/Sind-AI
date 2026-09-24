import unittest

from runtime.phase4.whatsapp_uia import descendant_pids, choose_window_candidate


class MsixDiscoveryTests(unittest.TestCase):
    def test_descendant_tree_contains_webview_children(self):
        processes = {
            10: {"pid": 10, "ppid": 1, "exe": "whatsapp.root.exe"},
            20: {"pid": 20, "ppid": 10, "exe": "msedgewebview2.exe"},
            21: {"pid": 21, "ppid": 20, "exe": "msedgewebview2.exe"},
            30: {"pid": 30, "ppid": 1, "exe": "explorer.exe"},
        }
        self.assertEqual(descendant_pids(processes, {10}), {10, 20, 21})

    def test_webview_main_window_is_selected(self):
        rows = [
            {
                "hwnd": 100,
                "pid": 20,
                "exe": "msedgewebview2.exe",
                "title": "(3) WhatsApp",
                "class_name": "Chrome_WidgetWin_1",
                "visible": True,
                "alpha_zero": False,
                "foreground": True,
                "bounds": [100, 100, 900, 800],
            },
            {
                "hwnd": 101,
                "pid": 21,
                "exe": "msedgewebview2.exe",
                "title": "",
                "class_name": "Chrome_WidgetWin_1",
                "visible": True,
                "alpha_zero": True,
                "foreground": False,
                "bounds": [0, 0, 1920, 1080],
            },
        ]
        chosen = choose_window_candidate(rows)
        self.assertEqual(chosen["hwnd"], 100)

    def test_transparent_helper_never_wins(self):
        rows = [
            {
                "hwnd": 1,
                "pid": 20,
                "exe": "msedgewebview2.exe",
                "title": "",
                "class_name": "Chrome_WidgetWin_1",
                "visible": True,
                "alpha_zero": True,
                "foreground": False,
                "bounds": [0, 0, 1920, 1080],
            }
        ]
        self.assertIsNone(choose_window_candidate(rows))

    def test_old_native_whatsapp_still_supported(self):
        rows = [
            {
                "hwnd": 2,
                "pid": 40,
                "exe": "whatsapp.exe",
                "title": "WhatsApp",
                "class_name": "ApplicationFrame",
                "visible": True,
                "alpha_zero": False,
                "foreground": False,
                "bounds": [20, 20, 900, 800],
            }
        ]
        self.assertEqual(choose_window_candidate(rows)["hwnd"], 2)


if __name__ == "__main__":
    unittest.main()
