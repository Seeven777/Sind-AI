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


class FakeTarget:
    def __init__(self, *, selection=True, enter=True, invoke=True, double=True):
        self.calls = []
        self._selection = selection
        self._enter = enter
        self._invoke = invoke
        self._double = double

    def is_visible(self):
        return True

    def is_enabled(self):
        return True

    @property
    def iface_selection_item(self):
        if not self._selection:
            raise RuntimeError("no selection")
        return _Selection(self)

    @property
    def iface_invoke(self):
        if not self._invoke:
            raise RuntimeError("no invoke")
        return _Invoke(self)

    def set_focus(self):
        self.calls.append("focus")

    def type_keys(self, keys, set_foreground=False):
        self.calls.append(("type_keys", keys, set_foreground))
        if not self._enter:
            raise RuntimeError("enter failed")

    def double_click_input(self):
        self.calls.append("double_click")
        if not self._double:
            raise RuntimeError("double failed")


class FakeWindow:
    def set_focus(self):
        pass


class TestUI(WhatsAppUIA):
    def __init__(self, target):
        super().__init__()
        self.controls = {"contact": target}
    def _attach(self):
        return FakeWindow()


class ConversationActivationTests(unittest.TestCase):
    def test_selection_item_uses_enter_after_selection(self):
        target = FakeTarget()
        TestUI(target).open_contact("contact")
        self.assertEqual(
            target.calls[:3],
            ["select", "focus", ("type_keys", "{ENTER}", True)],
        )
        self.assertNotIn("invoke", target.calls)
        self.assertNotIn("double_click", target.calls)

    def test_old_invoke_fallback_survives(self):
        target = FakeTarget(selection=False, invoke=True)
        TestUI(target).open_contact("contact")
        self.assertIn("invoke", target.calls)

    def test_double_click_is_last_fallback(self):
        target = FakeTarget(selection=False, invoke=False, double=True)
        TestUI(target).open_contact("contact")
        self.assertEqual(target.calls[-1], "double_click")

    def test_all_activation_failures_raise(self):
        target = FakeTarget(selection=False, enter=False, invoke=False, double=False)
        with self.assertRaises(RuntimeError):
            TestUI(target).open_contact("contact")


if __name__ == "__main__":
    unittest.main()
