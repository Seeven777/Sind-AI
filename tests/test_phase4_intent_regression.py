import unittest
from runtime.phase4.intent import classify_intent


class Phase4IntentRegressionTests(unittest.TestCase):
    def test_multiline_benchmark_is_executable_and_parsed(self):
        text = '''abra o WhatsApp
selecione a conversa Me (você)
escreva "teste fase 4" no campo de mensagem, mas não envie
envie a mensagem'''
        intent = classify_intent(text)
        self.assertTrue(intent.executable)
        self.assertTrue(intent.desktop)
        self.assertTrue(intent.whatsapp)
        self.assertEqual(intent.contact, 'Me (você)')
        self.assertEqual(intent.message, 'teste fase 4')

    def test_authorization_prefix_does_not_break_multiline(self):
        text = '''autorizo a ação física
abra o WhatsApp
selecione a conversa Me (você)
escreva "teste fase 4" no campo de mensagem, mas não envie
envie a mensagem'''
        intent = classify_intent(text)
        self.assertTrue(intent.executable)
        self.assertTrue(intent.whatsapp)
        self.assertEqual(intent.contact, 'Me (você)')
        self.assertEqual(intent.message, 'teste fase 4')

    def test_type_but_do_not_send_is_still_execution_not_send(self):
        text = '''abra o WhatsApp
selecione a conversa Me (você)
escreva "rascunho seguro" no campo de mensagem, mas não envie'''
        intent = classify_intent(text)
        self.assertTrue(intent.executable)
        self.assertTrue(intent.desktop)
        self.assertFalse(intent.whatsapp)

    def test_pure_negative_does_not_authorize(self):
        self.assertFalse(classify_intent('não abra o WhatsApp').executable)
        self.assertFalse(classify_intent('não envie nada pelo WhatsApp').executable)

    def test_information_question_stays_informative(self):
        intent = classify_intent('Como enviar uma mensagem pelo WhatsApp Desktop?')
        self.assertFalse(intent.executable)
        self.assertFalse(intent.whatsapp)

    def test_explicit_send_form_still_works(self):
        intent = classify_intent('Envie no WhatsApp para Me (você): teste literal')
        self.assertTrue(intent.executable)
        self.assertTrue(intent.whatsapp)
        self.assertEqual(intent.contact, 'Me (você)')
        self.assertEqual(intent.message, 'teste literal')

    def test_open_plus_negative_send_executes_open_only(self):
        intent = classify_intent('Abra o WhatsApp, mas não envie mensagem alguma.')
        self.assertTrue(intent.executable)
        self.assertTrue(intent.desktop)
        self.assertFalse(intent.whatsapp)


if __name__ == '__main__':
    unittest.main()
