import unittest

from runtime.phase4.whatsapp_interactive import (
    InteractiveWhatsAppIntent,
    WhatsAppInteractiveExecutor,
    parse_whatsapp_interactive,
)


class FakeWhatsAppUI:
    def __init__(self):
        self.opened = False
        self.search_value = ""
        self.selected_contact = ""
        self.draft = ""
        self.messages = []
        self.counter = 0

    def open(self):
        self.opened = True

    def observe(self, contact, message):
        controls = [
            {
                "key": "search", "name": "Search", "automation_id": "SearchBox",
                "control_type": "Edit", "visible": True, "enabled": True,
                "password": False, "read_only": False, "focused": False,
                "bounds": [0, 0, 250, 40],
            },
            {
                "key": "composer", "name": "Type a message", "automation_id": "MessageInput",
                "control_type": "Edit", "visible": True, "enabled": True,
                "password": False, "read_only": False, "focused": True,
                "bounds": [260, 500, 900, 550],
            },
        ]
        contacts = []
        if contact and self.search_value == contact:
            contacts = [{"name": contact, "key": "contact"}]
        conversation = contact if contact and self.selected_contact == contact else ""
        return {
            "ok": True,
            "complete": True,
            "controls": controls,
            "contacts": contacts,
            "conversation": conversation,
            "composer": "composer" if self.selected_contact else None,
            "draft": self.draft if self.selected_contact else None,
            "search_value": self.search_value,
            "messages": list(self.messages),
        }

    def set_text(self, key, text):
        if key == "search":
            self.search_value = text
        elif key == "composer":
            self.draft = text
        else:
            raise RuntimeError("unknown field")

    def open_contact(self, key):
        if key != "contact" or not self.search_value:
            raise RuntimeError("contact unavailable")
        self.selected_contact = self.search_value

    def send(self, contact, message):
        if self.selected_contact != contact or self.draft != message:
            raise RuntimeError("wrong current state")
        self.counter += 1
        self.messages.append({
            "id": f"m{self.counter}", "text": message,
            "outgoing": True, "state": "sent",
        })
        self.draft = ""


class ParserTests(unittest.TestCase):
    def test_select_conversation_compound_open(self):
        cmd = parse_whatsapp_interactive(
            "abra o WhatsApp\nselecione a conversa Me (você)",
            state=None,
        )
        self.assertIsNotNone(cmd)
        self.assertTrue(cmd.select)
        self.assertEqual(cmd.contact, "Me (você)")
        self.assertFalse(cmd.send)

    def test_type_but_do_not_send(self):
        cmd = parse_whatsapp_interactive(
            'escreva "teste fase 4" no campo de mensagem, mas não envie',
            state={"contact": "Me (você)", "draft": ""},
        )
        self.assertIsNotNone(cmd)
        self.assertTrue(cmd.type_text)
        self.assertEqual(cmd.message, "teste fase 4")
        self.assertFalse(cmd.send)

    def test_write_in_open_whatsapp_chat(self):
        cmd = parse_whatsapp_interactive(
            'escreva no chat aberto do whatsapp: "teste 1"',
            state={"contact": "Me (você)", "draft": ""},
        )
        self.assertIsNotNone(cmd)
        self.assertTrue(cmd.type_text)
        self.assertEqual(cmd.message, "teste 1")

    def test_send_current_is_continuation_only(self):
        self.assertIsNone(parse_whatsapp_interactive("envie a mensagem", state=None))
        cmd = parse_whatsapp_interactive(
            "envie a mensagem",
            state={"contact": "Me (você)", "draft": "teste 1"},
        )
        self.assertIsNotNone(cmd)
        self.assertTrue(cmd.send)
        self.assertFalse(cmd.type_text)

    def test_question_is_not_action(self):
        self.assertIsNone(parse_whatsapp_interactive(
            "Como enviar uma mensagem pelo WhatsApp Desktop?",
            state={"contact": "Me (você)"},
        ))

    def test_full_atomic_send_is_left_for_existing_executor(self):
        self.assertIsNone(parse_whatsapp_interactive(
            "Envie no WhatsApp para Me (você): teste fase 4",
            state={"contact": "Me (você)"},
        ))


class ExecutorTests(unittest.TestCase):
    def test_select_type_send_cycle(self):
        ui = FakeWhatsAppUI()
        ex = WhatsAppInteractiveExecutor(ui, timeout=0.05, poll=0.001)

        selected = ex.select_conversation("Me (você)")
        self.assertTrue(selected["goal_verification"]["verified"])

        typed = ex.type_draft("Me (você)", "teste fase 4")
        self.assertTrue(typed["goal_verification"]["verified"])
        self.assertEqual(ui.draft, "teste fase 4")
        self.assertEqual(ui.messages, [])

        sent = ex.send_current(
            "Me (você)", "teste fase 4",
            confirm=lambda *_: True,
            require_confirmation=True,
        )
        self.assertTrue(sent["goal_verification"]["verified"])
        self.assertEqual(ui.draft, "")
        self.assertEqual(len(ui.messages), 1)

    def test_type_preserves_other_existing_draft(self):
        ui = FakeWhatsAppUI()
        ui.selected_contact = "Me (você)"
        ui.draft = "não sobrescrever"
        ex = WhatsAppInteractiveExecutor(ui, timeout=0.02, poll=0.001)
        result = ex.type_draft("Me (você)", "novo")
        self.assertFalse(result["goal_verification"]["verified"])
        self.assertEqual(ui.draft, "não sobrescrever")

    def test_confirmation_denial_does_not_send(self):
        ui = FakeWhatsAppUI()
        ui.selected_contact = "Me (você)"
        ui.draft = "teste"
        ex = WhatsAppInteractiveExecutor(ui, timeout=0.02, poll=0.001)
        result = ex.send_current(
            "Me (você)", "teste",
            confirm=lambda *_: False,
            require_confirmation=True,
        )
        self.assertFalse(result["goal_verification"]["verified"])
        self.assertFalse(result["tool_execution"]["send_attempted"])
        self.assertEqual(ui.messages, [])
        self.assertEqual(ui.draft, "teste")


class RoutingRegressionTests(unittest.TestCase):
    def test_intent_marks_desktop_write_as_executable(self):
        from runtime.phase4.intent import classify_intent
        intent = classify_intent('escreva "teste fase 4" no campo de mensagem, mas não envie')
        self.assertTrue(intent.executable)
        self.assertTrue(intent.desktop)
        self.assertFalse(intent.whatsapp)

    def test_how_to_question_remains_informational(self):
        from runtime.phase4.intent import classify_intent
        intent = classify_intent('Como enviar uma mensagem pelo WhatsApp Desktop?')
        self.assertFalse(intent.executable)

    def test_fast_path_does_not_truncate_compound_whatsapp_command(self):
        from pathlib import Path
        from core.router import fast_path
        self.assertIsNone(fast_path(
            'abra o WhatsApp\nselecione a conversa Me (você)',
            Path('/tmp/Desktop'),
        ))

    def test_fast_path_keeps_atomic_open(self):
        from pathlib import Path
        from core.router import fast_path
        name, args = fast_path('abra o WhatsApp', Path('/tmp/Desktop'))
        self.assertEqual(name, 'open_app')
        self.assertEqual(args.get('app'), 'whatsapp')


if __name__ == "__main__":
    unittest.main()
