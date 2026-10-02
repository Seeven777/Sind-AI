"""Generic Windows desktop controller used by Jarvis.

Computer Runtime V2 keeps the public DeepAccessController interface compatible
with the existing agent while making the implementation less app-specific.
"""
from __future__ import annotations

import time
import unicodedata
from dataclasses import dataclass

from pywinauto import Desktop

from runtime.computer_v2 import (
    ComputerV2Error,
    copy_focused_text,
    focus_hwnd,
    normalize_key_expression,
    paste_unicode,
    point_in_bounds,
    send_key_expression,
    click_physical,
    visible_area,
)
from runtime.phase4.controls import choose_text_field, describe_control


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

ACTIONABLE_TYPES = {
    "Button", "Hyperlink", "MenuItem", "ListItem", "DataItem", "TabItem",
    "CheckBox", "RadioButton", "TreeItem", "Custom", "Group",
}


def _fold(value):
    return "".join(
        c for c in unicodedata.normalize("NFD", str(value or "").casefold())
        if unicodedata.category(c) != "Mn"
    )


@dataclass
class SelectedWindow:
    handle: int
    title: str


class DeepAccessController:
    """Semantic UIA first, verified physical input fallback second."""

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
                rect = win.rectangle()
                bounds = [rect.left, rect.top, rect.right, rect.bottom]
                if visible_area(bounds) <= 0:
                    continue
                items.append({
                    "title": title,
                    "handle": handle,
                    "visible": bool(win.is_visible()),
                    "enabled": bool(win.is_enabled()),
                    "bounds": bounds,
                    "process_id": int(win.element_info.process_id or 0),
                })
            except Exception:
                continue
        return {"ok": True, "windows": items[:180]}

    def select_window(self, query):
        query = str(query or "").strip()
        if not query:
            return {"ok": False, "error": "Informe o nome da janela."}

        data = self.list_windows()
        if not data.get("ok"):
            return data

        wanted = _fold(query)
        scored = []
        for item in data.get("windows", []):
            title = _fold(item["title"])
            if title == wanted:
                score = 1000
            elif title.startswith(wanted):
                score = 850
            elif wanted in title:
                score = 700
            else:
                tokens = [t for t in wanted.split() if len(t) >= 2]
                hits = sum(1 for token in tokens if token in title)
                if not tokens or hits != len(tokens):
                    continue
                score = 500 + hits
            if item.get("visible"):
                score += 20
            scored.append((score, -len(item["title"]), item))

        if not scored:
            return {"ok": False, "error": f"Nenhuma janela encontrada para: {query}"}

        scored.sort(reverse=True, key=lambda row: (row[0], row[1]))
        best = scored[0][2]
        self.selected = SelectedWindow(int(best["handle"]), best["title"])
        focus_hwnd(self.selected.handle)
        try:
            self._get_selected_wrapper().set_focus()
        except Exception:
            pass
        return {"ok": True, "title": best["title"], "handle": best["handle"]}

    def _get_selected_wrapper(self):
        if not self.selected:
            raise RuntimeError("Nenhuma janela foi selecionada.")
        win = self._desktop().window(handle=self.selected.handle)
        if not win.exists(timeout=0.6):
            raise RuntimeError("A janela selecionada não está mais disponível.")
        return win

    def _focus_selected(self):
        if not self.selected:
            raise RuntimeError("Nenhuma janela foi selecionada.")
        focus_hwnd(self.selected.handle)
        try:
            self._get_selected_wrapper().set_focus()
        except Exception:
            pass

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
                    "right": rect.right, "bottom": rect.bottom,
                },
            }
        except Exception:
            return {
                "selected": False,
                "title": self.selected.title,
                "handle": self.selected.handle,
                "stale": True,
            }

    def _rows(self, max_controls=4000):
        win = self._get_selected_wrapper()
        rows = []
        wrappers = {}
        for index, ctrl in enumerate(win.descendants()[: int(max_controls)]):
            try:
                key = index
                row = describe_control(ctrl, key)
                # UIA visibility is unreliable in some WebView2/WinUI surfaces.
                # Keep geometrically real controls as inspectable data.
                if not row.get("visible") and visible_area(row.get("bounds")) <= 20:
                    continue
                rows.append(row)
                wrappers[key] = ctrl
            except Exception:
                continue
        return rows, wrappers

    def inspect_selected(self, max_controls=90):
        try:
            rows, _ = self._rows(max_controls=max(100, int(max_controls) * 4))
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        useful = [
            row for row in rows
            if row.get("name") or row.get("automation_id") or row.get("control_type") in (
                "Edit", "Document", "Button", "Hyperlink", "MenuItem", "ListItem", "DataItem"
            )
        ][: int(max_controls)]
        return {
            "ok": True,
            "window": self.selected.title,
            "count": len(useful),
            "controls": useful,
        }

    def _control_score(self, row, wanted, wanted_type=None):
        if wanted_type and _fold(row.get("control_type")) != _fold(wanted_type):
            return 0
        if not row.get("enabled"):
            return 0
        name = _fold(row.get("name"))
        aid = _fold(row.get("automation_id"))
        label = (name + " " + aid).strip()
        if not wanted:
            return 0
        if name == wanted or aid == wanted:
            score = 1000
        elif name.startswith(wanted) or aid.startswith(wanted):
            score = 850
        elif wanted in name or wanted in aid:
            score = 700
        else:
            tokens = [t for t in wanted.split() if len(t) >= 2]
            if not tokens or any(token not in label for token in tokens):
                return 0
            score = 500 + len(tokens) * 5
        if row.get("control_type") in ACTIONABLE_TYPES:
            score += 60
        if row.get("focused"):
            score += 20
        if row.get("visible"):
            score += 10
        return score

    def _find_control(self, name, control_type=None):
        wanted = _fold(name).strip()
        rows, wrappers = self._rows()
        ranked = []
        for row in rows:
            score = self._control_score(row, wanted, control_type)
            if score:
                ranked.append((score, visible_area(row.get("bounds")), row, wrappers[row["key"]]))
        if not ranked:
            return None
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        if len(ranked) > 1 and ranked[0][0] == ranked[1][0] and ranked[0][1] == ranked[1][1]:
            a = ranked[0][2]
            b = ranked[1][2]
            if a.get("bounds") != b.get("bounds"):
                raise RuntimeError("Controle ambíguo; informe um nome ou automation_id mais específico.")
        return ranked[0][3]

    def _actionable_ancestor(self, ctrl, win):
        current = ctrl
        best = ctrl
        for _ in range(8):
            try:
                info = current.element_info
                ctype = str(info.control_type or "")
                if ctype in ACTIONABLE_TYPES:
                    best = current
                for attr in ("iface_invoke", "iface_selection_item", "iface_toggle"):
                    try:
                        getattr(current, attr)
                        return current
                    except Exception:
                        pass
                parent = current.parent()
                if parent is None or parent == current or parent == win:
                    break
                current = parent
            except Exception:
                break
        return best

    def _ui_signature(self):
        try:
            win = self._get_selected_wrapper()
            data = []
            for ctrl in win.descendants()[:350]:
                try:
                    info = ctrl.element_info
                    name = str(info.name or "").strip()
                    ctype = str(info.control_type or "")
                    if name:
                        data.append((ctype, name[:80]))
                except Exception:
                    continue
            return hash(tuple(data))
        except Exception:
            return None

    def is_risky_control(self, name):
        low = _fold(name)
        return any(_fold(word) in low for word in RISKY_CONTROL_WORDS)

    def is_sensitive_field(self, name):
        low = _fold(name)
        return any(_fold(word) in low for word in SENSITIVE_FIELD_WORDS)

    def click_control(self, name, control_type=None):
        try:
            ctrl = self._find_control(name, control_type)
            if ctrl is None:
                return {"ok": False, "error": f"Controle não encontrado: {name}"}
            if not ctrl.is_enabled():
                return {"ok": False, "error": f"O controle está desabilitado: {name}"}

            win = self._get_selected_wrapper()
            target = self._actionable_ancestor(ctrl, win)
            actual_name = str(target.element_info.name or ctrl.element_info.name or name).strip()
            actual_type = str(target.element_info.control_type or "").strip()
            before = self._ui_signature()
            self._focus_selected()
            method = None

            try:
                target.iface_invoke.Invoke()
                method = "invoke"
            except Exception:
                pass

            if method is None:
                try:
                    target.iface_selection_item.Select()
                    # Selection alone is not considered activation. Follow with a
                    # real physical click on the selected target.
                except Exception:
                    pass
                try:
                    rect = target.rectangle()
                    point = point_in_bounds(
                        [rect.left, rect.top, rect.right, rect.bottom], 0.5, 0.5
                    )
                    click_physical(*point)
                    method = "physical_click"
                except Exception:
                    try:
                        target.click_input()
                        method = "click_input"
                    except Exception as exc:
                        return {"ok": False, "error": f"Falha ao acionar controle: {exc}"}

            time.sleep(0.12)
            after = self._ui_signature()
            changed = before is not None and after is not None and before != after
            return {
                "ok": True,
                "name": actual_name or name,
                "control_type": actual_type,
                "method": method,
                "window": self.selected.title,
                "ui_changed": changed,
                "verification": {
                    "verified": bool(changed),
                    "scope": "tool",
                    "reason": (
                        "A interface observada mudou após a ativação."
                        if changed else
                        "A entrada física foi executada, mas não houve mudança UIA suficiente para provar o objetivo."
                    ),
                },
            }
        except Exception as exc:
            return {"ok": False, "error": f"Falha ao acionar controle: {exc}"}

    def _focused_control(self, rows, wrappers):
        focused = [(row, wrappers[row["key"]]) for row in rows if row.get("focused")]
        if len(focused) == 1:
            return focused[0]
        return None

    def type_text(self, text, control_name=None, clear_first=False):
        """Type exact Unicode into a verified editable target.

        ValuePattern is preferred. Keyboard/clipboard is a fallback only after the
        field itself has been identified and focused.
        """
        try:
            rows, wrappers = self._rows()
            if control_name and self.is_sensitive_field(control_name):
                return {"ok": False, "error": "Campo sensível não pode ser preenchido por esta ferramenta."}

            try:
                row = choose_text_field(rows, name=control_name)
                target = wrappers[row["key"]]
            except Exception:
                focused = self._focused_control(rows, wrappers)
                if control_name or not focused:
                    raise
                row, target = focused
                if row.get("control_type") not in ("Edit", "Document"):
                    raise RuntimeError("O controle focado não é um campo de texto reconhecido.")

            if self.is_sensitive_field(row.get("name") or row.get("automation_id")):
                return {"ok": False, "error": "Campo sensível não pode ser preenchido por esta ferramenta."}

            self._focus_selected()
            try:
                target.set_focus()
            except Exception:
                pass

            expected = str(text)
            old = None
            try:
                old = str(target.iface_value.CurrentValue)
                if not bool(target.iface_value.CurrentIsReadOnly):
                    expected = str(text) if clear_first else old + str(text)
                    target.iface_value.SetValue(expected)
                    actual = str(target.iface_value.CurrentValue)
                    verified = actual == expected
                    return {
                        "ok": verified,
                        "window": self.selected.title,
                        "target": row.get("name") or row.get("automation_id"),
                        "chars": len(str(text)),
                        "text_verified": verified,
                        "method": "ValuePattern.SetValue",
                        "verification": {
                            "verified": verified,
                            "scope": "tool",
                            "reason": "Valor exato relido pelo ValuePattern após a escrita.",
                        },
                        **({"error": "O texto escrito não pôde ser relido exatamente."} if not verified else {}),
                    }
            except Exception:
                pass

            # ContentEditable/WebView2 fallback.
            try:
                rect = target.rectangle()
                click_physical(*point_in_bounds([rect.left, rect.top, rect.right, rect.bottom]))
            except Exception:
                pass
            paste_unicode(str(text), clear_first=bool(clear_first), hwnd=self.selected.handle)
            actual = copy_focused_text(hwnd=self.selected.handle, select_all=True, collapse=True)
            expected = str(text) if clear_first or old is None else old + str(text)
            verified = actual == expected
            return {
                "ok": verified,
                "window": self.selected.title,
                "target": row.get("name") or row.get("automation_id") or "campo focado",
                "chars": len(str(text)),
                "text_verified": verified,
                "method": "physical_keyboard_clipboard",
                "verification": {
                    "verified": verified,
                    "scope": "tool",
                    "reason": (
                        "Texto exato foi copiado de volta do campo após a digitação física."
                        if verified else
                        "A digitação física ocorreu, mas o texto exato não pôde ser relido do campo."
                    ),
                },
                **({"error": "Não consegui verificar o texto exato no campo após digitar."} if not verified else {}),
            }
        except Exception as exc:
            return {"ok": False, "error": f"Falha ao digitar: {exc}"}

    def press_key(self, key):
        try:
            self._focus_selected()
            sequence = normalize_key_expression(key)
            send_key_expression(key)
            return {
                "ok": True,
                "key": str(key),
                "sequence": sequence,
                "window": self.selected.title,
                "verification": {
                    "verified": False,
                    "scope": "tool",
                    "reason": "A tecla/atalho foi injetada fisicamente; a pós-condição deve ser verificada pelo objetivo.",
                },
            }
        except (ComputerV2Error, Exception) as exc:
            return {"ok": False, "error": str(exc)}
