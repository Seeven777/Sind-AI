"""Windows-only UI Automation adapter. No coordinates, OCR or web fallback.

Controls are reacquired for every observation. Unknown WhatsApp accessibility
layouts fail closed; an accessible label alone never proves delivery.
"""
import ctypes
import os
import re
from pathlib import PureWindowsPath
from .controls import choose_text_field, describe_control
from .intent import fold, identity


def process_basename(pid):
    from ctypes import wintypes
    dll = ctypes.WinDLL('kernel32', use_last_error=True)
    dll.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    dll.OpenProcess.restype = wintypes.HANDLE
    dll.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    dll.QueryFullProcessImageNameW.restype = wintypes.BOOL
    dll.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = dll.OpenProcess(0x1000, False, int(pid))
    if not handle:
        return ''
    try:
        size = wintypes.DWORD(32768)
        buf = ctypes.create_unicode_buffer(size.value)
        if dll.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return PureWindowsPath(buf.value).name.casefold()
        return ''
    finally:
        dll.CloseHandle(handle)


def message_evidence(label, automation_id, child_names, message):
    """Positive direction AND positive send state required; fail closed otherwise."""
    normalized = fold(label)
    aid = fold(automation_id)
    outgoing = bool(re.search(r'^(?:voce|you)\s*:', normalized) or
                    any(x in aid for x in ('outgoingmessage', 'sentmessage', 'messagemine')))
    # Whole body in a child, or explicit sender/body + bounded metadata suffix.
    body = message in child_names
    if not body:
        body = any(label.startswith(prefix + message + separator)
                   for prefix in ('Você: ', 'You: ', 'você: ', 'you: ')
                   for separator in ('\n', ', ', '. '))
    metadata_label = label.replace(message, '') if message else label
    joined = fold('\n'.join([metadata_label] + [x for x in child_names if x != message]))
    if re.search(r'\b(?:pending|sending|failed|not sent|nao enviad[ao]|enviando|pendente|falha|retry|tentar novamente)\b', joined):
        state = 'pending_or_failed'
    elif re.search(r'\b(?:read|lida|lido)\b', joined):
        state = 'read'
    elif re.search(r'\b(?:delivered|entregue)\b', joined):
        state = 'delivered'
    elif re.search(r'\b(?:sent|enviada|enviado)\b', joined):
        state = 'sent'
    else:
        state = 'unknown'
    return {'text': message if body else '', 'outgoing': outgoing, 'state': state}


class WhatsAppUIA:
    def __init__(self):
        self.window = None
        self.controls = {}
        self.generation = 0

    def _attach(self):
        if os.name != 'nt':
            raise RuntimeError('WhatsApp Desktop UIA exige Windows com sessão gráfica desbloqueada.')
        from pywinauto import Desktop
        wins = []
        for win in Desktop(backend='uia').windows():
            try:
                if win.is_visible() and process_basename(win.element_info.process_id) == 'whatsapp.exe':
                    wins.append(win)
            except Exception:
                continue
        if len(wins) != 1:
            raise RuntimeError('Não há uma única janela nativa WhatsApp.exe acessível. Verifique instalação, login e diálogos abertos.')
        self.window = wins[0]
        return self.window

    def open(self):
        if os.name != 'nt':
            raise RuntimeError('Execução desktop disponível somente no Windows.')
        try:
            self._attach().set_focus()
        except RuntimeError:
            os.startfile('whatsapp:')

    def _value(self, ctrl):
        try:
            return str(ctrl.iface_value.CurrentValue)
        except Exception:
            return None

    def observe(self, contact, message):
        self.generation += 1
        self.controls = {}
        try:
            win = self._attach()
            descendants = win.descendants()
            complete = len(descendants) <= 4000
            rows = []
            wrappers = {}
            for index, ctrl in enumerate(descendants[:4000]):
                try:
                    key = f'{self.generation}:{index}'
                    item = describe_control(ctrl, key)
                    if not item['visible']:
                        continue
                    rows.append(item)
                    wrappers[key] = ctrl
                except Exception:
                    complete = False
            self.controls = wrappers
            result = {'ok': True, 'complete': complete, 'controls': rows, 'contacts': [],
                      'conversation': '', 'composer': None, 'draft': None, 'search_value': None, 'messages': []}
            try:
                search = choose_text_field(rows, purpose='search')
                search_rect = search['bounds']
                result['search_value'] = self._value(wrappers[search['key']])
                # Results must be list items in the search/sidebar column, not chat text.
                seen = set()
                for row in rows:
                    if row['control_type'] not in ('ListItem', 'DataItem') or not row['enabled']:
                        continue
                    rect = row['bounds']
                    if rect[0] > search_rect[2] or rect[1] < search_rect[3]:
                        continue
                    ctrl = wrappers[row['key']]
                    names = [row['name']] + [c.element_info.name or '' for c in ctrl.descendants(control_type='Text')]
                    if any(identity(n) == identity(contact) for n in names):
                        rid = tuple(ctrl.element_info.runtime_id or ())
                        if rid and rid not in seen:
                            result['contacts'].append({'name': contact, 'key': row['key']})
                            seen.add(rid)
            except RuntimeError:
                pass
            try:
                composer = choose_text_field(rows, purpose='message')
                result['composer'] = composer['key']
                result['draft'] = self._value(wrappers[composer['key']])
                rect = composer['bounds']
                wr = win.rectangle()
                headers = [r for r in rows if r['control_type'] in ('Text', 'Button')
                           and identity(r['name']) == identity(contact)
                           and r['bounds'][0] >= rect[0] - 30
                           and r['bounds'][1] < wr.top + (wr.bottom - wr.top) * .22]
                if len(headers) == 1:
                    result['conversation'] = contact
                # Read only message containers in the conversation column above composer.
                seen = set()
                for row in rows:
                    if row['control_type'] not in ('ListItem', 'DataItem', 'Group'):
                        continue
                    if row['bounds'][0] < rect[0] - 30 or row['bounds'][3] > rect[1]:
                        continue
                    ctrl = wrappers[row['key']]
                    children = [c.element_info.name or '' for c in ctrl.descendants()]
                    evidence = message_evidence(row['name'], row['automation_id'], children, message)
                    if not evidence['text']:
                        continue
                    rid = tuple(ctrl.element_info.runtime_id or ())
                    if not rid:
                        complete = False
                        continue
                    if rid not in seen and evidence['outgoing']:
                        result['messages'].append({'id': repr(rid), **evidence})
                        seen.add(rid)
            except RuntimeError:
                pass
            result['complete'] = complete
            return result
        except Exception as exc:
            return {'ok': False, 'complete': False, 'error': str(exc), 'controls': [], 'messages': []}

    def _target(self, key):
        ctrl = self.controls.get(key)
        if ctrl is None or not ctrl.is_visible() or not ctrl.is_enabled():
            raise RuntimeError('Controle UIA ausente, obsoleto ou desabilitado.')
        self._attach().set_focus()
        return ctrl

    def set_text(self, key, text):
        target = self._target(key)
        choose_text_field([describe_control(target, key)])
        target.set_focus()
        # SetValue is literal, preserves Unicode, and cannot interpret Enter/macros.
        target.iface_value.SetValue(str(text))

    def open_contact(self, key):
        target = self._target(key)
        # Invoke is preferred; selection/click is not blindly retried on errors.
        try:
            invoke = target.iface_invoke
        except Exception:
            target.click_input()
        else:
            invoke.Invoke()

    def send(self, contact, message):
        # Fresh pre-send observation prevents stale focus/header from authorizing send.
        snap = self.observe(contact, message)
        if identity(snap.get('conversation')) != identity(contact) or snap.get('draft') != message or not snap.get('complete'):
            raise RuntimeError('Conversa/campo mudou antes de enviar; operação interrompida.')
        composer = choose_text_field(snap['controls'], purpose='message')
        rect = composer['bounds']
        buttons = [c for c in snap['controls'] if c['control_type'] == 'Button'
                   and c['enabled'] and fold(c['name']).strip() in ('enviar', 'send', 'enviar mensagem', 'send message')
                   and c['bounds'][0] >= rect[0] and abs(c['bounds'][1] - rect[1]) < 100]
        if len(buttons) != 1:
            raise RuntimeError('Botão Enviar ausente ou ambíguo; não foi usado Enter como alternativa.')
        target = self._target(buttons[0]['key'])
        target.iface_invoke.Invoke()  # Exactly one attempt. No click fallback after invoke.
