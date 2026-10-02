import ast
import json
import copy
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from runtime.phase4.intent import classify_intent
from runtime.phase4.controls import choose_text_field
from runtime.phase4.whatsapp import WhatsAppExecutor, verify_message, summarize_whatsapp
from runtime.phase4.whatsapp_uia import message_evidence
from runtime.phase4.runtime import (ExecutionSession, DESKTOP_TOOLS, DESKTOP_ACTIONS, MUTATING_TOOLS,
                                    observe_desktop, WHATSAPP_SCHEMA)
from runtime.verifier import ResultVerifier

ROOT = Path(__file__).resolve().parents[1]


def field(key, name, **extra):
    return {'key': key, 'name': name, 'automation_id': '', 'control_type': 'Edit',
            'visible': True, 'enabled': True, 'read_only': False, 'password': False,
            **extra}


class FakeUI:
    """Stateful simulated UI: observations change only after physical adapter calls."""
    def __init__(self, mode='success'):
        self.mode = mode
        self.opened = False
        self.search = ''
        self.chat = ''
        self.draft = ''
        self.sent = False
        self.send_calls = 0
        self.writes = []
        self.observations = 0

    def open(self):
        if self.mode == 'missing_app':
            raise RuntimeError('WhatsApp ausente')
        self.opened = True

    def set_text(self, key, text):
        self.writes.append((key, text))
        if key == 'search':
            self.search = text
        elif key == 'composer':
            self.draft = text if self.mode != 'wrong_draft' else 'ERRADO'
        else:
            raise AssertionError('wrong target')

    def open_contact(self, key):
        self.chat = 'Outra pessoa' if self.mode == 'wrong_chat' else self.search
        if self.mode == 'existing_draft':
            self.draft = 'rascunho pessoal'

    def send(self, contact, message):
        self.send_calls += 1
        if self.mode == 'send_exception':
            raise RuntimeError('UIA disconnected after Invoke')
        self.sent = True
        self.message = message
        if self.mode != 'uncleared':
            self.draft = ''

    def observe(self, contact, message):
        self.observations += 1
        if not self.opened:
            return {'ok': False, 'controls': []}
        contacts = [{'name': contact, 'key': 'contact'}] if self.search else []
        if self.mode == 'ambiguous_contact':
            contacts *= 2
        if self.mode == 'no_contact':
            contacts = []
        controls = [field('search', 'Pesquisar')]
        if self.chat:
            controls += [field('composer', 'Digite uma mensagem')]
        if self.mode == 'ambiguous_composer' and self.chat:
            controls += [field('composer2', 'Digite uma mensagem')]
        messages = [{'id': 'old', 'text': message, 'outgoing': True, 'state': 'sent'}]
        if self.sent and self.mode != 'stale':
            messages.append({'id': 'new', 'text': message, 'outgoing': self.mode != 'incoming',
                             'state': 'pending' if self.mode == 'pending' else 'sent'})
        return {'ok': True, 'complete': self.mode != 'incomplete', 'controls': controls,
                'contacts': contacts, 'conversation': self.chat, 'composer': 'composer' if self.chat else None,
                'draft': self.draft, 'search_value': self.search, 'messages': messages}


def executor(ui, **kwargs):
    return WhatsAppExecutor(ui, timeout=.001, poll=0, **kwargs)


class IntentTests(unittest.TestCase):
    def test_informational_never_authorizes(self):
        for text in ('Como enviar uma mensagem no WhatsApp?', 'Me explique como abrir o WhatsApp',
                     'Não envie no WhatsApp para Maria: Oi', 'Simule enviar no WhatsApp para Maria: Oi',
                     'Escreva uma mensagem para enviar no WhatsApp', 'Você pode explicar como enviar no WhatsApp?',
                     'Gostaria de saber como enviar uma mensagem', 'Envie no WhatsApp, mas não envie ainda', 'O que significa "envie no WhatsApp"?'):
            with self.subTest(text=text):
                self.assertFalse(classify_intent(text).executable)

    def test_explicit_payload_forms(self):
        for text in ('Envie no WhatsApp para Maria Silva: Olá, ação! 🐶',
                     'Envie "Olá, ação! 🐶" para Maria Silva no WhatsApp',
                     'Abra o WhatsApp e envie para Maria Silva a mensagem "Olá, ação! 🐶"'):
            with self.subTest(text=text):
                intent = classify_intent(text)
                self.assertTrue(intent.whatsapp)
                self.assertEqual((intent.contact, intent.message), ('Maria Silva', 'Olá, ação! 🐶'))

    def test_payload_preserves_channel_words_quotes_and_colons(self):
        intent = classify_intent('Envie no WhatsApp para Maria: Responda "Oi": só no WhatsApp!')
        self.assertEqual(intent.message, 'Responda "Oi": só no WhatsApp!')
        intent = classify_intent('Envie "Responda no WhatsApp!" para Maria no WhatsApp.')
        self.assertEqual((intent.contact, intent.message), ('Maria', 'Responda no WhatsApp!'))

    def test_indirect_request_is_executable(self):
        self.assertTrue(classify_intent('Você pode enviar no WhatsApp para Ana: Oi?').executable)

    def test_missing_details_do_not_invent(self):
        for text in ('Mande uma mensagem no WhatsApp', 'Envie no WhatsApp para Maria e João: Oi'):
            self.assertEqual(classify_intent(text).message, '')

    def test_action_words_in_payload_do_not_change_request(self):
        value = classify_intent('Envie no WhatsApp para Maria: Não envie nada ainda!')
        self.assertTrue(value.whatsapp)
        self.assertEqual(value.message, 'Não envie nada ainda!')

    def test_open_only_is_not_send(self):
        value = classify_intent('Abra o WhatsApp')
        self.assertTrue(value.desktop)
        self.assertFalse(value.whatsapp)


class SelectorTests(unittest.TestCase):
    def test_message_not_search(self):
        rows = [field('search', 'Pesquisar'), field('message', 'Digite uma mensagem')]
        self.assertEqual(choose_text_field(rows, purpose='message')['key'], 'message')

    def test_no_first_edit_fallback(self):
        with self.assertRaises(RuntimeError):
            choose_text_field([field(1, 'Busca'), field(2, 'Texto')])

    def test_focused_and_explicit_id(self):
        rows = [field(1, 'Busca'), field(2, '', focused=True, automation_id='BodyInput')]
        self.assertEqual(choose_text_field(rows)['key'], 2)
        self.assertEqual(choose_text_field(rows, name='BodyInput')['key'], 2)

    def test_reject_unsafe_fields(self):
        for extra in ({'password': True}, {'read_only': True}, {'enabled': False}, {'visible': False}, {'control_type': 'Button'}):
            with self.subTest(extra=extra), self.assertRaises(RuntimeError):
                choose_text_field([field(1, 'Mensagem', **extra)])
        with self.assertRaises(RuntimeError):
            choose_text_field([field(1, 'Password')])

    def test_ambiguous_message_boxes(self):
        with self.assertRaises(RuntimeError):
            choose_text_field([field(1, 'Digite uma mensagem'), field(2, 'Type a message')], purpose='message')


class WhatsAppTests(unittest.TestCase):
    def test_success_requires_new_outgoing_evidence_and_exact_unicode(self):
        ui = FakeUI()
        result = executor(ui).run('Maria Silva', 'Olá! 🐶\nLinha 2', confirm=lambda *_: True)
        self.assertTrue(result['goal_verification']['verified'])
        self.assertEqual(ui.send_calls, 1)
        self.assertEqual(ui.writes, [('search', 'Maria Silva'), ('composer', 'Olá! 🐶\nLinha 2')])
        phases = [x['phase'] for x in result['events']]
        self.assertEqual(phases[0], 'observe')
        self.assertEqual(phases[-1], 'verify')
        self.assertGreater(phases.count('observe'), phases.count('act'))

    def test_pre_send_failures_do_not_send(self):
        for mode in ('missing_app', 'no_contact', 'ambiguous_contact', 'wrong_chat', 'existing_draft',
                     'wrong_draft', 'ambiguous_composer', 'incomplete'):
            with self.subTest(mode=mode):
                ui = FakeUI(mode)
                result = executor(ui).run('Maria', 'Oi', confirm=lambda *_: True)
                self.assertFalse(result['ok'])
                self.assertEqual(ui.send_calls, 0)
                self.assertFalse(result['goal_verification']['verified'])

    def test_uncertain_never_retries_or_succeeds(self):
        for mode in ('stale', 'incoming', 'pending', 'uncleared', 'send_exception'):
            with self.subTest(mode=mode):
                ui = FakeUI(mode)
                result = executor(ui).run('Maria', 'Oi', confirm=lambda *_: True)
                self.assertEqual(ui.send_calls, 1)
                self.assertEqual(result['status'], 'uncertain')
                self.assertFalse(result['goal_verification']['verified'])
                self.assertIn('Envio incerto', summarize_whatsapp(result))
                if mode != 'send_exception':
                    self.assertTrue(result['tool_execution']['ok'])

    def test_denial_or_missing_callback_stops_before_draft(self):
        for confirm in (None, lambda *_: False):
            ui = FakeUI()
            result = executor(ui).run('Maria', 'Oi', confirm=confirm)
            self.assertFalse(result['ok'])
            self.assertEqual(ui.send_calls, 0)
            self.assertEqual(ui.writes, [('search', 'Maria')])

    def test_user_changes_chat_during_confirmation(self):
        ui = FakeUI()
        def confirm(*_):
            ui.chat = 'Outra pessoa'
            return True
        result = executor(ui).run('Maria', 'Oi', confirm=confirm)
        self.assertFalse(result['ok'])
        self.assertEqual(ui.send_calls, 0)

    def test_cancelled_before_effects(self):
        ui = FakeUI()
        def cancelled():
            raise RuntimeError('Cancelado')
        result = executor(ui, cancelled=cancelled).run('Maria', 'Oi', confirm=lambda *_: True)
        self.assertFalse(ui.opened)
        self.assertFalse(result['ok'])

    def test_logging_failure_does_not_retry_send(self):
        ui = FakeUI()
        def bad_log(*_):
            raise RuntimeError('disk full')
        result = executor(ui, event=bad_log).run('Maria', 'Oi', confirm=lambda *_: True)
        self.assertTrue(result['ok'])
        self.assertEqual(ui.send_calls, 1)

    def test_runtime_id_change_without_count_increase_is_not_evidence(self):
        before = {'complete': True, 'conversation': 'Maria', 'messages': [{'id': 'a', 'text': 'Oi', 'outgoing': True, 'state': 'sent'}]}
        after = {'ok': True, 'complete': True, 'conversation': 'Maria', 'draft': '', 'messages': [{'id': 'b', 'text': 'Oi', 'outgoing': True, 'state': 'sent'}]}
        self.assertFalse(verify_message(before, after, 'Maria', 'Oi'))

    def test_recipient_identity_does_not_remove_accents(self):
        before = {'complete': True, 'conversation': 'José', 'messages': []}
        after = {'ok': True, 'complete': True, 'conversation': 'José', 'draft': '',
                 'messages': [{'id': 'new', 'text': 'Oi', 'outgoing': True, 'state': 'sent'}]}
        self.assertFalse(verify_message(before, after, 'Jose', 'Oi'))

    def test_metadata_words_in_message_are_not_send_state(self):
        self.assertEqual(message_evidence('Você: enviado', 'OutgoingMessage', ['enviado'], 'enviado')['state'], 'unknown')
        evidence = message_evidence('Você: Oi, enviada às 10:30', 'OutgoingMessage', ['Oi'], 'Oi')
        self.assertEqual(evidence['state'], 'sent')
        self.assertTrue(evidence['outgoing'])


class RuntimeTests(unittest.TestCase):
    def test_model_cannot_claim_success_without_tools(self):
        session = ExecutionSession('Envie no WhatsApp para Maria: Oi')
        self.assertIn('Não concluí', session.final_answer('Pronto! Enviei com sucesso.'))

    def test_plan_read_and_successful_click_cannot_complete_goal(self):
        session = ExecutionSession('Clique em enviar no aplicativo')
        for name in ('set_task_plan', 'inspect_selected_window', 'click_control'):
            session.record(name, {}, {'ok': True, 'verification': {'verified': True}})
        self.assertFalse(session.goal_verification()['verified'])
        self.assertNotIn('Pronto', session.final_answer('Pronto, concluído.'))

    def test_tool_success_does_not_mean_verification(self):
        verifier = ResultVerifier()
        for name in ('press_key', 'click_control', 'execute_action', 'run_skill', 'execute_workflow', 'unknown'):
            self.assertFalse(verifier.verify(name, {}, {'ok': True})['verified'])

    def test_informational_answer_preserved(self):
        session = ExecutionSession('Como enviar uma mensagem?')
        self.assertEqual(session.final_answer('Abra o aplicativo e escolha o contato.'), 'Abra o aplicativo e escolha o contato.')

    def test_literal_typing_can_complete_only_after_re_read(self):
        session = ExecutionSession('digite "Olá, mundo!"')
        session.record('type_text', {'text': 'Olá, mundo!'}, {'ok': True, 'verification': {'verified': True}})
        self.assertTrue(session.goal_verification()['verified'])
        self.assertIn('Texto inserido', session.final_answer('inventado'))

    def test_unknown_compound_goal_cannot_use_one_verified_step(self):
        session = ExecutionSession('Abra o WhatsApp e envie uma mensagem')
        session.record('open_app', {'app': 'whatsapp'}, {'ok': True, 'verification': {'verified': True}})
        self.assertFalse(session.goal_verification()['verified'])


def agent_harness():
    """Execute actual agent methods without importing Windows-only UI dependencies.

    Only external collaborators are faked, not dispatch/routing/completion logic.
    """
    module = ast.parse((ROOT / 'core/agent.py').read_text(encoding='utf-8'))
    agent = next(x for x in module.body if isinstance(x, ast.ClassDef) and any(isinstance(n, ast.FunctionDef) and n.name == 'dispatch' for n in x.body))
    methods = {'_execution_session', '_tools_for_prompt', 'dispatch', '_run_unlocked', '_run_whatsapp_goal', '_run_internal'}
    body = [n for n in agent.body if isinstance(n, ast.FunctionDef) and n.name in methods]
    namespace = dict(globals(), WhatsAppUIA=lambda: FakeUI(), ensure_portuguese_response=lambda text, *_args, **_kw: text)
    import time, re
    namespace.update(time=time, re=re)
    tree = ast.Module(body=[ast.ClassDef(name='Harness', bases=[], keywords=[], body=body, decorator_list=[])], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), str(ROOT / 'core/agent.py'), 'exec'), namespace)
    h = namespace['Harness']()
    h.config = {'phase4_timeout_seconds': .001}
    h._phase4_context = threading.local()
    h._phase4_context.session = None
    h._cancel_event = threading.Event()
    h._check_cancelled = lambda: None
    h._last_response_metadata = {}
    h.verifier = ResultVerifier()
    h.deep_access = MagicMock()
    h.deep_access.snapshot.return_value = {}
    h.deep_access.inspect_selected.return_value = {'ok': True, 'controls': []}
    h.skills = MagicMock()
    h.skills.relevant_skills.return_value = []
    h.tool_schema_by_name = {n: {'function': {'name': n}} for n in DESKTOP_TOOLS}
    h.tool_schema_by_name['create_file'] = {'function': {'name': 'create_file'}}
    h._dispatch_unverified = MagicMock(return_value={'ok': True})
    for name in ('tasks', 'models', 'conversations', 'learning', 'reflections', 'projects', 'experience', 'diagnostics'):
        setattr(h, name, MagicMock())
    h.tasks.start.return_value = 1
    h.projects.current_id.return_value = None
    h.learning.learn_from_user.return_value = {}
    h.reflections.reflect.return_value = {}
    h.experience.observe_feedback.return_value = {}
    h.semantic = SimpleNamespace(enabled=False)
    return h, namespace


class IntegrationTests(unittest.TestCase):
    def test_automatic_desktop_schemas_survive_tool_budget(self):
        h, _ = agent_harness()
        tools = h._tools_for_prompt('Envie no WhatsApp para Maria: Oi')
        self.assertTrue(set(DESKTOP_TOOLS).issubset({x['function']['name'] for x in tools}))

    def test_public_boundary_prevents_language_model_reintroducing_success(self):
        h, namespace = agent_harness()
        h._run_internal = lambda *_args, **_kw: 'Não executei'
        namespace['ensure_portuguese_response'] = lambda *_args, **_kw: 'Enviei com sucesso!'
        answer = h._run_unlocked('Envie no WhatsApp para Maria: Oi')
        self.assertIn('Não concluí', answer)
        self.assertIsNone(h._execution_session())
        self.assertEqual(h.learning.record_episode.call_args.kwargs['status'], 'failed')

    def test_direct_whatsapp_route_bypasses_conversation_and_verifies(self):
        h, _ = agent_harness()
        answer = h._run_unlocked('Envie no WhatsApp para Maria: Oi', confirm_callback=lambda *_: True)
        self.assertIn('Mensagem enviada', answer)
        self.assertEqual(h.tasks.finish.call_args.kwargs['status'], 'completed')
        self.assertEqual(h.learning.record_episode.call_args.kwargs['status'], 'completed')

    def test_partial_request_asks_details_without_tools(self):
        h, _ = agent_harness()
        answer = h._run_unlocked('Envie mensagem no WhatsApp')
        self.assertIn('contato exato', answer)
        h._dispatch_unverified.assert_not_called()

    def test_tool_cannot_invent_recipient_or_payload(self):
        h, _ = agent_harness()
        h._phase4_context.session = ExecutionSession('Envie no WhatsApp para Maria: Oi')
        result = h.dispatch('whatsapp_send_message', {'contact': 'João', 'message': 'Outro'})
        self.assertFalse(result['ok'])

    def test_dispatch_without_current_authorization_blocks_send(self):
        h, _ = agent_harness()
        self.assertFalse(h.dispatch('whatsapp_send_message', {'contact': 'Maria', 'message': 'Oi'})['ok'])

    def test_same_session_never_sends_twice(self):
        h, namespace = agent_harness()
        ui = FakeUI('stale')
        namespace['WhatsAppUIA'] = lambda: ui
        h._phase4_context.session = ExecutionSession('Envie no WhatsApp para Maria: Oi')
        for _ in range(2):
            h.dispatch('whatsapp_send_message', {'contact': 'Maria', 'message': 'Oi'}, confirm_callback=lambda *_: True)
        self.assertEqual(ui.send_calls, 1)

    def test_uncertainty_persists_as_failure_not_learning_success(self):
        h, namespace = agent_harness()
        namespace['WhatsAppUIA'] = lambda: FakeUI('stale')
        answer = h._run_unlocked('Envie no WhatsApp para Maria: Oi', confirm_callback=lambda *_: True)
        self.assertIn('Envio incerto', answer)
        self.assertEqual(h.tasks.finish.call_args.kwargs['status'], 'failed')
        self.assertEqual(h.learning.record_episode.call_args.kwargs['status'], 'failed')

    def test_json_tool_arguments_are_decoded_and_invalid_objects_rejected(self):
        h, _ = agent_harness()
        self.assertTrue(h.dispatch('inspect_selected_window', '{}')['ok'])
        self.assertFalse(h.dispatch('open_app', 'invalid')['ok'])
        self.assertFalse(h.dispatch('open_app', [])['ok'])

    def test_informational_dispatch_cannot_act(self):
        h, _ = agent_harness()
        h._phase4_context.session = ExecutionSession('Como abrir o WhatsApp?')
        self.assertFalse(h.dispatch('open_app', {'app': 'whatsapp'})['ok'])
        h._dispatch_unverified.assert_not_called()


if __name__ == '__main__':
    unittest.main()
