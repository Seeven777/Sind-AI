import unittest

from runtime.phase4.whatsapp_uia import (
    _right_pane_contact_name_matches,
    _hit_chain_matches_contact,
)


class HitTestLogicTests(unittest.TestCase):
    def test_exact_header(self):
        self.assertTrue(
            _right_pane_contact_name_matches("Me (você)", "Me (você)")
        )

    def test_short_header_status_suffix(self):
        self.assertTrue(
            _right_pane_contact_name_matches(
                "Me (você) online",
                "Me (você)",
            )
        )

    def test_unrelated_header_rejected(self):
        self.assertFalse(
            _right_pane_contact_name_matches("Outra pessoa", "Me (você)")
        )

    def test_hit_chain_accepts_search_row_parent(self):
        hit = {
            "chain": [
                {"name": "texto filho", "control_type": "Text"},
                {
                    "name": "Me (você) 07:11 22 fichas = 210R$",
                    "control_type": "DataItem",
                },
            ]
        }
        self.assertTrue(_hit_chain_matches_contact(hit, "Me (você)"))

    def test_hit_chain_rejects_different_contact(self):
        hit = {
            "chain": [
                {
                    "name": "Maria Silva 07:11 Oi",
                    "control_type": "DataItem",
                }
            ]
        }
        self.assertFalse(_hit_chain_matches_contact(hit, "Me (você)"))


if __name__ == "__main__":
    unittest.main()
