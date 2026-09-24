"""Deterministic observe/act/observe/verify; never retry a send operation."""
import time
from .controls import choose_text_field
from .intent import fold, identity


def verify_message(before, after, contact, message):
    if not after.get('ok') or not after.get('complete') or not before.get('complete'):
        return False
    if identity(after.get('conversation')) != identity(contact) or identity(before.get('conversation')) != identity(contact):
        return False
    if after.get('draft') != '':
        return False
    old = before.get('messages', [])
    current = after.get('messages', [])
    old_ids = {x.get('id') for x in old}
    matches = lambda rows: [x for x in rows if x.get('text') == message and x.get('outgoing')]
    # A stale bubble, received text, toast, draft, or changed runtime id alone is insufficient.
    return len(matches(current)) > len(matches(old)) and any(
        x.get('id') and x['id'] not in old_ids and x.get('state') in ('sent', 'delivered', 'read')
        for x in matches(current))


class WhatsAppExecutor:
    def __init__(self, adapter, timeout=12, poll=0.25, cancelled=None, event=None):
        self.ui = adapter
        self.timeout = max(0.01, min(float(timeout), 30))
        self.poll = poll
        self.cancelled = cancelled or (lambda: None)
        self.event = event or (lambda *args: None)
        self.events = []
        self.send_attempted = False

    def emit(self, entry):
        try:
            self.event(entry)
        except Exception:
            # Logging failure must not lose an uncertain send or trigger a retry.
            pass

    def observe(self, contact, message):
        self.cancelled()
        snap = self.ui.observe(contact, message)
        # Persist evidence summaries, never an entire chat history.
        entry = {'phase': 'observe', 'ok': bool(snap.get('ok')),
                 'conversation': snap.get('conversation'), 'complete': snap.get('complete'),
                 'message_count': len(snap.get('messages', [])), 'draft_chars': len(snap.get('draft') or '')}
        self.events.append(entry)
        self.emit(entry)
        return snap

    def wait(self, contact, message, predicate, reason):
        deadline = time.monotonic() + self.timeout
        while True:
            snap = self.observe(contact, message)
            if snap.get('ok') and predicate(snap):
                return snap
            if time.monotonic() >= deadline:
                raise RuntimeError(reason)
            time.sleep(self.poll)

    def act(self, name, *args):
        self.cancelled()
        self.events.append({'phase': 'act', 'action': name})
        self.emit(self.events[-1])
        return getattr(self.ui, name)(*args)

    def run(self, contact, message, confirm=None, require_confirmation=True):
        tool_ok = False
        try:
            if not contact or not message or len(message) > 10000:
                raise RuntimeError('Informe um contato e uma mensagem explícitos (até 10.000 caracteres).')
            self.observe(contact, message)
            self.act('open')
            snap = self.wait(contact, message, lambda s: bool(s.get('controls')), 'WhatsApp Desktop não ficou acessível via UI Automation.')
            search = choose_text_field(snap['controls'], purpose='search')
            self.act('set_text', search['key'], contact)
            snap = self.wait(contact, message, lambda s: s.get('search_value') == contact and bool(s.get('contacts')), 'Contato exato não encontrado na pesquisa.')
            candidates = [x for x in snap['contacts'] if identity(x.get('name')) == identity(contact)]
            if len(candidates) != 1:
                raise RuntimeError('Contato ausente ou ambíguo. Use o nome único exibido no WhatsApp.')
            self.act('open_contact', candidates[0]['key'])
            snap = self.wait(contact, message, lambda s: identity(s.get('conversation')) == identity(contact) and bool(s.get('composer')), 'Não confirmei o cabeçalho da conversa solicitada.')
            composer = choose_text_field(snap['controls'], purpose='message')
            if snap.get('draft') not in ('', None):
                raise RuntimeError('A conversa já tem um rascunho. Ele foi preservado; limpe-o manualmente antes de tentar.')
            if snap.get('draft') is None:
                raise RuntimeError('Não consegui ler o campo de mensagem para verificar se está vazio.')
            # Policy confirmation happens before drafting; there is no effect on denial.
            if require_confirmation and (not confirm or not confirm('Enviar pelo WhatsApp Desktop', f'Contato: {contact}\n\nMensagem exata:\n{message}\n\nEnviar uma vez?')):
                raise RuntimeError('Envio não autorizado pela confirmação configurada; nenhuma mensagem enviada.')
            snap = self.observe(contact, message)
            if identity(snap.get('conversation')) != identity(contact) or snap.get('draft') != '':
                raise RuntimeError('A conversa ou o rascunho mudou durante a confirmação.')
            composer = choose_text_field(snap['controls'], purpose='message')
            self.act('set_text', composer['key'], message)
            before = self.wait(contact, message, lambda s: identity(s.get('conversation')) == identity(contact) and s.get('draft') == message, 'Não confirmei o texto exato no campo de mensagem.')
            if not before.get('complete'):
                raise RuntimeError('Árvore UIA incompleta; não é seguro enviar sem observação anterior completa.')
            self.cancelled()
            self.send_attempted = True  # Mark BEFORE invoking; exceptions may follow a real send.
            self.act('send', contact, message)
            tool_ok = True
            after = self.wait(contact, message, lambda s: verify_message(before, s, contact, message), 'Não encontrei uma nova mensagem de saída confirmada na conversa correta.')
            verification = {'verified': True, 'scope': 'goal', 'reason': 'Nova mensagem de saída com estado de envio observada na conversa correta.',
                            'conversation': after['conversation'], 'message_ids': [x['id'] for x in after['messages'] if x.get('text') == message]}
            self.events.append({'phase': 'verify', **verification})
            self.emit(self.events[-1])
            return {'ok': True, 'tool_execution': {'ok': True, 'send_attempted': True},
                    'goal_verification': verification, 'status': 'verified', 'events': self.events}
        except Exception as exc:
            reason = str(exc) or type(exc).__name__
            verification = {'verified': False, 'scope': 'goal', 'reason': reason}
            self.events.append({'phase': 'verify', **verification})
            self.emit(self.events[-1])
            return {'ok': False, 'tool_execution': {'ok': tool_ok, 'send_attempted': self.send_attempted},
                    'goal_verification': verification, 'status': 'uncertain' if self.send_attempted else 'failed',
                    'error': reason, 'events': self.events}


def summarize_whatsapp(result):
    if result.get('goal_verification', {}).get('verified'):
        return 'Mensagem enviada; confirmei uma nova mensagem de saída na conversa solicitada. Isso não confirma que o destinatário leu.'
    reason = result.get('error', 'Não foi possível verificar o objetivo.')
    if result.get('tool_execution', {}).get('send_attempted'):
        return 'Envio incerto: ' + reason + ' Não vou reenviar automaticamente. Confira a conversa no WhatsApp antes de tentar novamente.'
    return 'Não concluí o envio: ' + reason
