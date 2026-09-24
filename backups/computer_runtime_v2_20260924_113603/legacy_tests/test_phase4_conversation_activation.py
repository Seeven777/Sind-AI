import unittest
from runtime.phase4.whatsapp_uia import WhatsAppUIA


class _Invoke:
    def __init__(self, owner):
        self.owner = owner
    def Invoke(self):
        self.owner.calls.append("invoke")


class FakeTarget:
    def __init__(self, rect=(100, 100, 300, 160), invoke=True):
        self.calls = []
        self._rect = rect
        self._invoke = invoke

    def is_visible(self):
        return True

    def is_enabled(self):
        return True

    def rectangle(self):
        l, t, r, b = self._rect
        return type("R", (), {"left":l, "top":t,"right":r,"bottom":b})()

    def parent(self):
        return None

    @property
    def element_info(self):
        return type("EI", (), {
            "control_type":"DataItem",
            "name":"Me (você) 07:11",
        })()

    @property
    def iface_invoke(self):
        if not self._invoke:
            raise RuntimeError("no invoke")
        return _Invoke(self)


class TestUI(WhatsAppUIA):
    def __init__(self, target, activation_results):
        super().__init__()
        self.controls = {"contact": target}
        self.contact_names = {"contact":"Me (você)"}
        self._activation_results = list(activation_results)

    def _target(self, key):
        return self.controls[key]

    def _conversation_header_present(self, contact):
        return False

    def _try_physical_row_activation(self, target, contact, double=False, variant=0):
        target.calls.append(("physical", double, variant))
        if self._activation_results:
            return self._activation_results.pop(0)
        return False

    def _reacquire_contact_target(self, contact, timeout=5.0):
        self.controls["contact"] = FakeTarget(invoke=self.controls["contact"]._invoke)
        return self.controls["contact"]

    def _wait_conversation_header(self, contact, timeout=1.5):
        return False


class ConversationActivationTests(unittest.TestCase):
    def test_first_verified_physical_click_completes(self):
        target = FakeTarget()
        TestUI(target, [True]).open_contact("contact")
        self.assertEqual(target.calls, [("physical", False, 0)])

    def test_second_attempt_reacquires_before_retry(self):
        target = FakeTarget()
        ui = TestUI(target, [False, True])
        ui.open_contact("contact")
        self.assertEqual(target.calls, [("physical", False, 0)])

    def test_double_click_is_only_after_two_single_failures(self):
        target = FakeTarget()
        ui = TestUI(target, [False, False, True])
        ui.open_contact("contact")
        # Success is provided by the third physical activation.
        self.assertEqual(len(ui._activation_results), 0)

    def test_failure_is_reported_if_every_verified_activation_fails(self):
        target = FakeTarget(invoke=False)
        ui = TestUI(target, [False, False, False])
        with self.assertRaises(RuntimeError):
            ui.open_contact("contact")


if __name__ == "__main__":
    unittest.main()
