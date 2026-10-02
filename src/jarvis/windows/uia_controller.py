from __future__ import annotations

import os


class WindowsAutomationUnavailable(RuntimeError):
    pass


class WindowsUIAController:
    """Windows UI Automation via pywinauto.

    UIA is preferred over coordinate-based mouse automation. The dependency is
    optional so Windows automation failures cannot prevent Jarvis from starting.
    """

    def available(self):
        if os.name!='nt':
            return False
        try:
            import pywinauto  # noqa:F401
            return True
        except Exception:
            return False

    def health(self):
        return {
            'status':'healthy' if self.available() else 'unavailable',
            'backend':'pywinauto-uia',
            'platform':os.name,
        }

    def _desktop(self):
        if not self.available():
            raise WindowsAutomationUnavailable(
                'Windows UI Automation indisponível. Use Setup-Jarvis-Extras.cmd.'
            )
        from pywinauto import Desktop
        return Desktop(backend='uia')

    async def list_windows(self):
        desktop=self._desktop()
        result=[]
        for win in desktop.windows():
            try:
                title=win.window_text()
                if not title:
                    continue
                result.append({
                    'title':title,
                    'handle':int(win.handle),
                    'class_name':win.element_info.class_name,
                    'control_type':win.element_info.control_type,
                })
            except Exception:
                continue
        return result

    async def inspect(self,title_re,depth=2):
        desktop=self._desktop()
        win=desktop.window(title_re=title_re)
        win.wait('exists ready',timeout=10)
        items=[]
        for ctrl in win.descendants(depth=depth):
            try:
                info=ctrl.element_info
                items.append({
                    'title':ctrl.window_text(),
                    'control_type':info.control_type,
                    'automation_id':info.automation_id,
                    'class_name':info.class_name,
                })
            except Exception:
                continue
        return {'window':win.window_text(),'controls':items[:500]}

    async def interact(self,action):
        kind=action.get('kind')
        desktop=self._desktop()
        title_re=action.get('window_title_re') or '.*'
        win=desktop.window(title_re=title_re)
        win.wait('exists ready',timeout=float(action.get('timeout',10)))

        if kind=='activate':
            win.set_focus()
            return {'success':True,'window':win.window_text(),'action':'activate'}

        criteria={}
        if action.get('title') is not None:
            criteria['title']=action['title']
        if action.get('auto_id') is not None:
            criteria['auto_id']=action['auto_id']
        if action.get('control_type') is not None:
            criteria['control_type']=action['control_type']
        control=win.child_window(**criteria) if criteria else win

        if kind=='click':
            control.wait('exists enabled visible',timeout=float(action.get('timeout',10)))
            control.click_input()
            return {'success':True,'window':win.window_text(),'action':'click','criteria':criteria}
        if kind=='set_text':
            control.wait('exists enabled visible',timeout=float(action.get('timeout',10)))
            text=str(action.get('text',''))
            try:
                control.set_edit_text(text)
            except Exception:
                control.set_focus()
                control.type_keys('^a{BACKSPACE}',set_foreground=True)
                control.type_keys(text,with_spaces=True,set_foreground=True)
            return {
                'success':True,'window':win.window_text(),
                'action':'set_text','criteria':criteria,'chars':len(text)
            }
        if kind=='type_keys':
            keys=str(action.get('keys',''))
            win.set_focus()
            win.type_keys(keys,with_spaces=True,set_foreground=True)
            return {'success':True,'window':win.window_text(),'action':'type_keys'}
        raise ValueError(f"Ação UIA não suportada: {kind}")
