import unittest
from runtime.phase4.intent import classify_intent
from runtime.phase4.whatsapp_uia import contact_row_matches


class ContactSelectionTests(unittest.TestCase):
    def setUp(self):
        self.search = [20, 20, 420, 65]

    def row(self, name, ctype="Text", bounds=None, visible=True, enabled=True):
        return {
            "name": name,
            "control_type": ctype,
            "bounds": bounds or [25, 80, 390, 125],
            "visible": visible,
            "enabled": enabled,
        }

    def test_exact_text_result_is_accepted_even_as_text(self):
        self.assertTrue(contact_row_matches(self.row("Me (você)"), "Me (você)", self.search))

    def test_container_type_is_not_required(self):
        self.assertTrue(contact_row_matches(
            self.row("Me (você)", ctype="Custom"), "Me (você)", self.search
        ))

    def test_result_above_search_is_rejected(self):
        self.assertFalse(contact_row_matches(
            self.row("Me (você)", bounds=[25, 5, 390, 40]), "Me (você)", self.search
        ))

    def test_partial_name_is_not_enough(self):
        self.assertFalse(contact_row_matches(self.row("Me"), "Me (você)", self.search))


class IntentRegressionTests(unittest.TestCase):
    def test_capitalization_preserved(self):
        i = classify_intent('Envie "Olá" para Maria Silva no WhatsApp')
        self.assertEqual((i.contact, i.message), ("Maria Silva", "Olá"))

    def test_message_keyword_not_part_of_contact(self):
        i = classify_intent('Abra o WhatsApp e envie para Maria Silva a mensagem "Olá"')
        self.assertEqual((i.contact, i.message), ("Maria Silva", "Olá"))

    def test_send_then_cancel_without_other_action_is_not_executable(self):
        self.assertFalse(classify_intent("Envie no WhatsApp, mas não envie ainda").executable)

    def test_multiple_recipients_are_not_invented(self):
        i = classify_intent("Envie no WhatsApp para Maria e João: Oi")
        self.assertEqual((i.contact, i.message), ("", ""))

    def test_payload_channel_words_preserved(self):
        i = classify_intent('Envie "Responda no WhatsApp!" para Maria no WhatsApp.')
        self.assertEqual((i.contact, i.message), ("Maria", "Responda no WhatsApp!"))


if __name__ == "__main__":
    unittest.main()
