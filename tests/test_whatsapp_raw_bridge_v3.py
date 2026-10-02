import unittest

from runtime.phase4.whatsapp_uia import (
    contact_accessible_name_matches,
    _raw_edit_score,
)


class _Rect:
    def __init__(self, l,t,r,b):
        self.left=l; self.top=t; self.right=r; self.bottom=b


class _Value:
    CurrentIsReadOnly = False
    CurrentValue = ""


class _Info:
    def __init__(self, name="", aid="", ctype="Edit"):
        self.name=name
        self.automation_id=aid
        self.control_type=ctype


class FakeEdit:
    def __init__(self, name="", aid="_r_f_", bounds=(1283,208,1407,229)):
        self.element_info=_Info(name, aid, "Edit")
        self._bounds=bounds
        self.iface_value=_Value()

    def rectangle(self):
        return _Rect(*self._bounds)
    def is_enabled(self):
        return True
    def is_visible(self):
        return True


class RawBridgeTests(unittest.TestCase):
    def test_empty_name_generated_id_search_is_still_strong(self):
        score, meta = _raw_edit_score(
            FakeEdit(name="", aid="_r_f_"),
            [1150,94,1884,923],
        )
        self.assertGreaterEqual(score, 400)
        self.assertEqual(meta["automation_id"], "_r_f_")

    def test_unlabeled_top_left_edit_without_known_id_still_has_evidence(self):
        score, meta = _raw_edit_score(
            FakeEdit(name="", aid="generated-x"),
            [1150,94,1884,923],
        )
        self.assertGreater(score, 200)

    def test_random_bottom_right_edit_is_not_as_strong(self):
        score, _ = _raw_edit_score(
            FakeEdit(name="", aid="x", bounds=(1600,800,1800,840)),
            [1150,94,1884,923],
        )
        self.assertLess(score, 250)

    def test_whatsapp_accessible_row_metadata_matches_exact_contact(self):
        self.assertTrue(contact_accessible_name_matches(
            "Me (você) 07:11 22 fichas = 210R$",
            "Me (você)",
        ))

    def test_longer_contact_does_not_match_shorter_person(self):
        self.assertFalse(contact_accessible_name_matches(
            "Maria Silva 07:11 Oi",
            "Maria",
        ))


if __name__ == "__main__":
    unittest.main()
