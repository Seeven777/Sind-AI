from __future__ import annotations

import os
import time


class WhatsAppUnavailable(RuntimeError):
    pass


class WhatsAppDesktopService:
    """Best-effort WhatsApp Desktop executor using Windows UI Automation.

    It never reports success unless the sent text is observed again in the chat.
    """

    SEARCH_HINTS=(
        'search or start new chat','search','pesquisar ou iniciar nova conversa',
        'pesquisar','buscar',
    )
    MESSAGE_HINTS=(
        'type a message','message','digite uma mensagem','mensagem',
    )

    def available(self):
        if os.name!='nt':return False
        try:
            import pywinauto  # noqa:F401
            return True
        except Exception:
            return False

    def health(self):
        if not self.available():
            return {'status':'unavailable','backend':'pywinauto-uia'}
        try:
            from pywinauto import Desktop
            wins=Desktop(backend='uia').windows(title_re='.*WhatsApp.*')
            return {
                'status':'healthy' if wins else 'not_running',
                'backend':'pywinauto-uia',
                'windows':len(wins),
            }
        except Exception as exc:
            return {'status':'error','error':str(exc)}

    def _window(self):
        if not self.available():
            raise WhatsAppUnavailable('pywinauto/Windows UIA indisponível.')
        from pywinauto import Desktop
        windows=Desktop(backend='uia').windows(title_re='.*WhatsApp.*')
        if not windows:
            raise WhatsAppUnavailable('WhatsApp Desktop não está aberto.')
        win=windows[0]
        win.set_focus()
        return win

    def _edit_controls(self,win):
        result=[]
        for ctrl in win.descendants(control_type='Edit'):
            try:
                if ctrl.is_visible() and ctrl.is_enabled():
                    result.append(ctrl)
            except Exception:
                continue
        return result

    def _pick_search(self,edits):
        for ctrl in edits:
            try:name=(ctrl.window_text() or ctrl.element_info.name or '').strip().lower()
            except Exception:name=''
            if any(h in name for h in self.SEARCH_HINTS):
                return ctrl
        return edits[0] if edits else None

    def _pick_message(self,edits,search_ctrl=None):
        candidates=[]
        for ctrl in edits:
            if search_ctrl is not None and ctrl.handle==search_ctrl.handle:
                continue
            try:name=(ctrl.window_text() or ctrl.element_info.name or '').strip().lower()
            except Exception:name=''
            score=2 if any(h in name for h in self.MESSAGE_HINTS) else 0
            candidates.append((score,ctrl))
        if not candidates:return None
        candidates.sort(key=lambda x:x[0])
        return candidates[-1][1]

    def _set_text(self,ctrl,text):
        ctrl.set_focus()
        try:
            ctrl.set_edit_text(text)
        except Exception:
            ctrl.type_keys('^a{BACKSPACE}',set_foreground=True)
            ctrl.type_keys(text,with_spaces=True,set_foreground=True)

    def send_message(self,contact,message,timeout=20):
        win=self._window()
        edits=self._edit_controls(win)
        search=self._pick_search(edits)
        if search is None:
            raise WhatsAppUnavailable('Campo de busca do WhatsApp não encontrado.')

        self._set_text(search,contact)
        deadline=time.time()+timeout
        target=None
        while time.time()<deadline:
            for ctrl in win.descendants(control_type='Text'):
                try:
                    name=(ctrl.window_text() or ctrl.element_info.name or '').strip()
                except Exception:
                    continue
                if name and contact.lower() in name.lower():
                    target=ctrl
                    break
            if target:break
            time.sleep(.25)
        if target is None:
            raise WhatsAppUnavailable(f'Contato não localizado: {contact}')
        target.click_input()
        time.sleep(.5)

        edits=self._edit_controls(win)
        message_box=self._pick_message(edits,search)
        if message_box is None:
            raise WhatsAppUnavailable('Campo de mensagem não encontrado.')
        self._set_text(message_box,message)
        message_box.type_keys('{ENTER}',set_foreground=True)

        deadline=time.time()+timeout
        observed=False
        observed_text=None
        needle=message.strip()
        while time.time()<deadline:
            for ctrl in win.descendants(control_type='Text'):
                try:
                    value=(ctrl.window_text() or ctrl.element_info.name or '').strip()
                except Exception:
                    continue
                if value and needle and needle in value:
                    observed=True;observed_text=value;break
            if observed:break
            time.sleep(.3)

        return {
            'success':observed,
            'contact':contact,
            'message':message,
            'sent_invoked':True,
            'verified':observed,
            'observed_text':observed_text,
            'window':win.window_text(),
        }
