import unittest
from pathlib import Path

from access.commands import parse_access_command
from core.router import fast_path
from runtime.computer_v2 import normalize_key_expression, point_in_bounds
from runtime.phase4.controls import choose_text_field


class ComputerPrimitiveTests(unittest.TestCase):
    def test_hotkeys(self):
        self.assertEqual(normalize_key_expression("ctrl+f"), "^f")
        self.assertEqual(normalize_key_expression("ctrl + shift + s"), "^+s")
        self.assertEqual(normalize_key_expression("pagedown"), "{PGDN}")

    def test_live_rect_point_never_uses_fixed_coordinate(self):
        self.assertEqual(point_in_bounds([100, 200, 500, 400], .5, .5), (300, 300))

    def test_access_parser_accepts_shortcut(self):
        self.assertEqual(
            parse_access_command("pressione ctrl+f"),
            {"action": "press_key", "key": "ctrl+f"},
        )

    def test_compound_whatsapp_is_not_truncated_by_fast_path(self):
        self.assertIsNone(
            fast_path("abra o WhatsApp\nselecione a conversa Me (você)", Path("C:/Desktop"))
        )

    def test_synthetic_composer_is_selectable(self):
        row = {
            "key": "composer:synthetic",
            "name": "Digite uma mensagem",
            "automation_id": "__jarvis_keyboard_composer__",
            "control_type": "Edit",
            "visible": True,
            "enabled": True,
            "password": False,
            "read_only": False,
            "focused": False,
            "bounds": [500, 800, 1200, 860],
            "synthetic": True,
        }
        self.assertEqual(choose_text_field([row], purpose="message")["key"], row["key"])


if __name__ == "__main__":
    unittest.main()
