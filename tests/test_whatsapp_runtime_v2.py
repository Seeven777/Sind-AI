import unittest
from runtime.phase4.whatsapp_uia import WhatsAppUIA


class TestUI(WhatsAppUIA):
    def __init__(self, click_results, keyboard=False):
        super().__init__()
        self.contact_names = {"k": "Me (você)"}
        self.click_results = list(click_results)
        self.keyboard_result = keyboard
        self.calls = []

    def _conversation_header_present(self, contact):
        return False

    def _fresh_hit_tested_click_contact(self, contact, double=False):
        self.calls.append(("double" if double else "click", "fresh"))
        if self.click_results:
            return self.click_results.pop(0)
        return False

    def _keyboard_activate_from_raw_search(self, contact):
        self.calls.append(("keyboard", "down-enter"))
        return self.keyboard_result


class WhatsAppOpenTests(unittest.TestCase):
    def test_first_fresh_click_can_open(self):
        ui = TestUI([True])
        ui.open_contact("k")
        self.assertEqual(ui.calls, [("click", "fresh")])

    def test_keyboard_is_second_strategy(self):
        ui = TestUI([False], keyboard=True)
        ui.open_contact("k")
        self.assertEqual(
            ui.calls,
            [("click", "fresh"), ("keyboard", "down-enter")],
        )

    def test_double_click_is_third_strategy(self):
        ui = TestUI([False, True], keyboard=False)
        ui.open_contact("k")
        self.assertEqual(
            ui.calls,
            [
                ("click", "fresh"),
                ("keyboard", "down-enter"),
                ("double", "fresh"),
            ],
        )

    def test_all_failed_attempts_fail_closed(self):
        ui = TestUI([False, False], keyboard=False)
        with self.assertRaises(RuntimeError):
            ui.open_contact("k")


if __name__ == "__main__":
    unittest.main()
