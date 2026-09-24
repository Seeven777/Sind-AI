import unittest
from runtime.phase4.whatsapp_uia import WhatsAppUIA


class _Selection:
    def __init__(self, owner):
        self.owner = owner
    def Select(self):
        self.owner.calls.append("select")


class _Invoke:
    def __init__(self, owner):
        self.owner = owner
    def Invoke(self):
        self.owner.calls.append("invoke")


class FakeWindow:
    def set_focus(self):
        return None


class FakeTarget:
    def __init__(self, focused=False):
        self.calls = []
        self.focused = focused

    def is_visible(self):
        return True

    def is_enabled(self):
        return True

    def click_input(self):
        self.calls.append("click")

    def double_click_input(self):
        self.calls.append("double_click")

    def set_focus(self):
        self.calls.append("set_focus")

    def has_keyboard_focus(self):
        self.calls.append("has_focus")
        return self.focused

    def type_keys(self, keys, set_foreground=False):
        self.calls.append(("enter", keys, set_foreground))

    @property
    def iface_selection_item(self):
        return _Selection(self)

    @property
    def iface_invoke(self):
        return _Invoke(self)


class TestUI(WhatsAppUIA):
    def __init__(self, target, verify_sequence):
        super().__init__()
        self.controls = {"k": target}
        self.contact_names = {"k": "Me (você)"}
        self.sequence = list(verify_sequence)

    def _attach(self):
        return FakeWindow()

    def _conversation_header_present(self, contact):
        if self.sequence:
            return self.sequence.pop(0)
        return False

    def _wait_conversation_header(self, contact, timeout=1.2):
        return self._conversation_header_present(contact)


class VerifiedActivationTests(unittest.TestCase):
    def test_single_click_stops_when_verified(self):
        target = FakeTarget()
        ui = TestUI(target, [False, True])
        ui.open_contact("k")
        self.assertEqual(target.calls, ["click"])

    def test_enter_is_skipped_without_verified_keyboard_focus(self):
        target = FakeTarget(focused=False)
        ui = TestUI(target, [False, False, True])
        ui.open_contact("k")
        self.assertIn("double_click", target.calls)
        self.assertFalse(any(isinstance(x, tuple) and x[0] == "enter" for x in target.calls))

    def test_enter_used_only_when_focus_is_verified(self):
        target = FakeTarget(focused=True)
        ui = TestUI(target, [False, False, True])
        ui.open_contact("k")
        self.assertTrue(any(isinstance(x, tuple) and x[0] == "enter" for x in target.calls))
        self.assertNotIn("double_click", target.calls)

    def test_fail_closed_if_no_activation_opens_chat(self):
        target = FakeTarget(focused=False)
        ui = TestUI(target, [False, False, False, False])
        with self.assertRaises(RuntimeError):
            ui.open_contact("k")


if __name__ == "__main__":
    unittest.main()
