import time
from dataclasses import dataclass

from pywinauto import Desktop, keyboard
from tools.clipboard import get_clipboard_text, set_clipboard_text

RISKY_CONTROL_WORDS = {
    "excluir", "apagar", "delete", "remove", "remover",
    "enviar", "send", "submit", "publicar", "publish",
    "comprar", "buy", "pagar", "pay", "transferir", "transfer",
    "instalar", "install", "desinstalar", "uninstall",
    "confirmar", "confirm", "finalizar", "finish",
    "aceitar", "accept", "autorizar", "authorize",
}

SENSITIVE_FIELD_WORDS = {
    "senha", "password", "passcode", "pin", "token",
    "secret", "segredo", "chave", "api key", "apikey",
    "cartão", "cartao", "card number", "cvv",
}

@dataclass
class SelectedWindow:
    handle: int
    title: str

class DeepAccessController:
    def __init__(self):
        self.selected = None

    def _desktop(self):
        return Desktop(backend="uia")

    def list_windows(self):
        items = []
        seen = set()
        try:
            windows = self._desktop().windows()
        except Exception as exc:
            return {"ok": False, "error": f"Falha ao enumerar janelas: {exc}"}

        for win in windows:
            try:
                title = (win.window_text() or "").strip()
                handle = int(win.handle)
                if not title or handle in seen:
                    continue
                seen.add(handle)
                items.append({
                    "title": title,
                    "handle": handle,
                    "visible": bool(win.is_visible()),
                    "enabled": bool(win.is_enabled()),
                })
            except Exception:
                continue
        return {"ok": True, "windows": items[:120]}

    def select_window(self, query):
        query = str(query).strip()
        if not query:
            return {"ok": False, "error": "Informe o nome da janela."}

        data = self.list_windows()
        if not data.get("ok"):
            return data

        low = query.lower()
        scored = []
        for item in data.get("windows", []):
            t = item["title"].lower()
            score = 0
            if t == low:
                score = 100
            elif t.startswith(low):
                score = 80
            elif low in t:
                score = 60
            else:
                tokens = [x for x in low.split() if len(x) >= 3]
                hits = sum(1 for token in tokens if token in t)
                if tokens and hits == len(tokens):
                    score = 40 + hits
            if score:
                scored.append((score, -len(item["title"]), item))

        if not scored:
            return {"ok": False, "error": f"Nenhuma janela encontrada para: {query}"}

        scored.sort(reverse=True, key=lambda x: (x[0], x[1]))
        item = scored[0][2]
        self.selected = SelectedWindow(int(item["handle"]), item["title"])

        try:
            self._get_selected_wrapper().set_focus()
        except Exception:
            pass

        return {"ok": True, "title": self.selected.title, "handle": self.selected.handle}

    def _get_selected_wrapper(self):
        if not self.selected:
            raise RuntimeError("Nenhuma janela foi selecionada.")
        win = self._desktop().window(handle=self.selected.handle)
        if not win.exists(timeout=0.6):
            raise RuntimeError("A janela selecionada não está mais disponível.")
        return win

    def snapshot(self):
        if not self.selected:
            return {"selected": False, "title": None, "handle": None}
        try:
            win = self._get_selected_wrapper()
            rect = win.rectangle()
            return {
                "selected": True,
                "title": self.selected.title,
                "handle": self.selected.handle,
                "rectangle": {
                    "left": rect.left, "top": rect.top,
                    "right": rect.right, "bottom": rect.bottom
                },
            }
        except Exception:
            return {"selected": False, "title": self.selected.title, "handle": self.selected.handle, "stale": True}

    def inspect_selected(self, max_controls=90):
        try:
            win = self._get_selected_wrapper()
            descendants = win.descendants()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        controls = []
        for ctrl in descendants:
            if len(controls) >= int(max_controls):
                break
            try:
                info = ctrl.element_info
                name = (info.name or "").strip()
                aid = (info.automation_id or "").strip()
                ctype = (info.control_type or "").strip()
                if not name and not aid:
                    continue
                controls.append({
                    "name": name,
                    "control_type": ctype,
                    "automation_id": aid,
                    "enabled": bool(ctrl.is_enabled()),
                    "visible": bool(ctrl.is_visible()),
                })
            except Exception:
                continue

        return {"ok": True, "window": self.selected.title, "count": len(controls), "controls": controls}

    def _find_control(self, name, control_type=None):
        win = self._get_selected_wrapper()
        wanted = str(name).strip().lower()
        wanted_type = str(control_type).strip().lower() if control_type else None
        matches = []

        for ctrl in win.descendants():
            try:
                info = ctrl.element_info
                cname = (info.name or "").strip()
                ctype = (info.control_type or "").strip()
                if wanted_type and ctype.lower() != wanted_type:
                    continue
                low = cname.lower()
                if low == wanted:
                    score = 100
                elif low.startswith(wanted):
                    score = 80
                elif wanted and wanted in low:
                    score = 60
                else:
                    continue
                matches.append((score, -len(cname), ctrl))
            except Exception:
                continue

        if not matches:
            return None
        matches.sort(reverse=True, key=lambda x: (x[0], x[1]))
        return matches[0][2]

    def is_risky_control(self, name):
        low = str(name).strip().lower()
        return any(word in low for word in RISKY_CONTROL_WORDS)

    def is_sensitive_field(self, name):
        low = str(name or "").strip().lower()
        return any(word in low for word in SENSITIVE_FIELD_WORDS)

    def click_control(self, name, control_type=None):
        try:
            ctrl = self._find_control(name, control_type)
            if ctrl is None:
                return {"ok": False, "error": f"Controle não encontrado: {name}"}
            if not ctrl.is_enabled():
                return {"ok": False, "error": f"O controle está desabilitado: {name}"}

            actual_name = (ctrl.element_info.name or "").strip()
            actual_type = (ctrl.element_info.control_type or "").strip()

            try:
                ctrl.invoke()
                method = "invoke"
            except Exception:
                ctrl.click_input()
                method = "click_input"

            return {
                "ok": True, "name": actual_name or name,
                "control_type": actual_type, "method": method,
                "window": self.selected.title
            }
        except Exception as exc:
            return {"ok": False, "error": f"Falha ao acionar controle: {exc}"}

    def type_text(self, text, control_name=None, clear_first=False):
        text = str(text)
        try:
            win = self._get_selected_wrapper()
            win.set_focus()
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

        target = None
        if control_name:
            if self.is_sensitive_field(control_name):
                return {"ok": False, "error": "Campo sensível bloqueado."}
            target = self._find_control(control_name)
            if target is None:
                return {"ok": False, "error": f"Campo não encontrado: {control_name}"}
        else:
            for ctrl in win.descendants():
                try:
                    ctype = (ctrl.element_info.control_type or "").lower()
                    cname = (ctrl.element_info.name or "").strip()
                    if ctype not in {"edit", "document"}:
                        continue
                    if self.is_sensitive_field(cname):
                        continue
                    if ctrl.is_enabled() and ctrl.is_visible():
                        target = ctrl
                        break
                except Exception:
                    continue

        try:
            if target is not None:
                target.set_focus()
            if clear_first:
                keyboard.send_keys("^a{BACKSPACE}")
                time.sleep(0.05)

            old = get_clipboard_text()
            old_text = old.get("text", "") if old.get("ok") else None

            set_clipboard_text(text)
            keyboard.send_keys("^v")
            time.sleep(0.08)

            if old_text is not None:
                set_clipboard_text(old_text)

            return {
                "ok": True, "window": self.selected.title,
                "target": ((target.element_info.name or "").strip() if target else None),
                "chars": len(text)
            }
        except Exception as exc:
            return {"ok": False, "error": f"Falha ao digitar: {exc}"}

    def press_key(self, key):
        aliases = {
            "enter": "{ENTER}", "tab": "{TAB}", "escape": "{ESC}", "esc": "{ESC}",
            "backspace": "{BACKSPACE}", "delete": "{DELETE}",
            "up": "{UP}", "down": "{DOWN}", "left": "{LEFT}", "right": "{RIGHT}",
        }
        wanted = str(key).strip().lower()
        if wanted not in aliases:
            return {"ok": False, "error": "Tecla não permitida nesta versão."}

        try:
            self._get_selected_wrapper().set_focus()
            keyboard.send_keys(aliases[wanted])
            return {"ok": True, "key": wanted, "window": self.selected.title}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
