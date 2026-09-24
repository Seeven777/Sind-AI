import unittest
from runtime.phase4.whatsapp_uia import WhatsAppUIA


class FakeTarget:
    def is_visible(self):
        return True

    def is_enabled(self):
        return True


class TestUI(WhatsAppUIA):
    """Pure mock for the V4 activation state machine."""

    def __init__(self, physical_results, keyboard_result=False):
        super().__init__()
        self.target = FakeTarget()
        self.controls = {"k": self.target}
        self.contact_names = {"k": "Me (você)"}
        self.physical_results = list(physical_results)
        self.keyboard_result = bool(keyboard_result)
        self.calls = []
        self.reacquires = 0

    def _target(self, key):
        return self.controls[key]

    def _conversation_header_present(self, contact):
        return False

    def _hit_tested_click_contact(self, target, contact, double=False):
        self.calls.append(("double" if double else "click", "hit-tested"))
        if self.physical_results:
            return self.physical_results.pop(0)
        return False

    def _keyboard_activate_raw_result(self, target, contact):
        self.calls.append(("keyboard", "selection-enter"))
        return self.keyboard_result

    def _raw_reacquire_contact(self, contact, timeout=3.0):
        self.reacquires += 1
        self.target = FakeTarget()
        self.controls["k"] = self.target
        return self.target


class WhatsAppOpenTests(unittest.TestCase):
    def test_first_hit_tested_click_can_open(self):
        ui = TestUI([True])
        ui.open_contact("k")
        self.assertEqual(ui.calls, [("click", "hit-tested")])
        self.assertEqual(ui.reacquires, 0)

    def test_keyboard_is_second_strategy_after_fresh_reacquire(self):
        ui = TestUI([False], keyboard_result=True)
        ui.open_contact("k")
        self.assertEqual(
            ui.calls,
            [
                ("click", "hit-tested"),
                ("keyboard", "selection-enter"),
            ],
        )
        self.assertEqual(ui.reacquires, 1)

    def test_double_click_is_third_strategy(self):
        ui = TestUI([False, True], keyboard_result=False)
        ui.open_contact("k")
        self.assertEqual(
            ui.calls,
            [
                ("click", "hit-tested"),
                ("keyboard", "selection-enter"),
                ("double", "hit-tested"),
            ],
        )
        self.assertEqual(ui.reacquires, 2)

    def test_all_failed_attempts_fail_closed(self):
        ui = TestUI([False, False], keyboard_result=False)
        with self.assertRaises(RuntimeError):
            ui.open_contact("k")


if __name__ == "__main__":
    unittest.main()
