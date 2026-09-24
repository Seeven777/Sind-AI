"""Low-level Windows computer control primitives for Sind AI / Jarvis.

Goals:
- no paid APIs;
- no fixed screen coordinates;
- physical input uses live UIA/window geometry;
- DPI-aware mouse input;
- clipboard-preserving Unicode typing;
- explicit verification helpers;
- no silent retries for irreversible effects.

This module deliberately contains no language-model logic.
"""
from __future__ import annotations

import contextlib
import os
import re
import time
import uuid


class ComputerV2Error(RuntimeError):
    pass


def _require_windows():
    if os.name != "nt":
        raise ComputerV2Error("Computer Runtime V2 requer Windows com sessão gráfica desbloqueada.")


@contextlib.contextmanager
def per_monitor_dpi_v2():
    """Temporarily make the current thread Per-Monitor-V2 DPI aware when possible."""
    if os.name != "nt":
        yield
        return

    import ctypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    setter = getattr(user32, "SetThreadDpiAwarenessContext", None)
    previous = None
    if setter is not None:
        try:
            setter.restype = ctypes.c_void_p
            setter.argtypes = [ctypes.c_void_p]
            # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 == (HANDLE)-4
            previous = setter(ctypes.c_void_p(-4))
        except Exception:
            previous = None
    try:
        yield
    finally:
        if setter is not None and previous:
            try:
                setter(ctypes.c_void_p(previous))
            except Exception:
                pass


def _root_hwnd(hwnd):
    """Return the top-level ancestor for any child/WebView HWND."""
    _require_windows()
    import ctypes
    from ctypes import wintypes

    hwnd = int(hwnd or 0)
    if not hwnd:
        return 0

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    GA_ROOT = 2
    user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
    user32.GetAncestor.restype = wintypes.HWND
    root = int(user32.GetAncestor(wintypes.HWND(hwnd), GA_ROOT) or 0)
    return root or hwnd


def focus_hwnd(hwnd):
    """Best-effort foreground activation using the TOP-LEVEL app HWND.

    WebView2 automation often attaches to Chrome_WidgetWin_1, which is a child
    renderer HWND. SetForegroundWindow on that child is unreliable. Always
    activate its GA_ROOT top-level owner instead.
    """
    _require_windows()
    import ctypes
    from ctypes import wintypes

    requested = int(hwnd or 0)
    hwnd = _root_hwnd(requested)
    if not hwnd:
        return False

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    SW_RESTORE = 9
    user32.ShowWindow(wintypes.HWND(hwnd), SW_RESTORE)

    foreground = int(user32.GetForegroundWindow() or 0)
    current_tid = int(kernel32.GetCurrentThreadId())
    foreground_tid = (
        int(user32.GetWindowThreadProcessId(wintypes.HWND(foreground), None))
        if foreground else 0
    )
    target_tid = int(
        user32.GetWindowThreadProcessId(wintypes.HWND(hwnd), None)
    )

    attached_fg = False
    attached_target = False
    try:
        if foreground_tid and foreground_tid != current_tid:
            attached_fg = bool(
                user32.AttachThreadInput(current_tid, foreground_tid, True)
            )
        if target_tid and target_tid != current_tid:
            attached_target = bool(
                user32.AttachThreadInput(current_tid, target_tid, True)
            )

        user32.ShowWindow(wintypes.HWND(hwnd), SW_RESTORE)
        user32.BringWindowToTop(wintypes.HWND(hwnd))
        user32.SetForegroundWindow(wintypes.HWND(hwnd))
        user32.SetActiveWindow(wintypes.HWND(hwnd))
    finally:
        if attached_target:
            user32.AttachThreadInput(current_tid, target_tid, False)
        if attached_fg:
            user32.AttachThreadInput(current_tid, foreground_tid, False)

    active = int(user32.GetForegroundWindow() or 0)
    if not active:
        return False
    return _root_hwnd(active) == hwnd


def _send_mouse_button(left_down=True):
    """Inject one mouse button event through SendInput; mouse_event is fallback."""
    _require_windows()
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    INPUT_MOUSE = 0
    MOUSEEVENTF_LEFTDOWN = 0x0002
    MOUSEEVENTF_LEFTUP = 0x0004
    flag = MOUSEEVENTF_LEFTDOWN if left_down else MOUSEEVENTF_LEFTUP

    ULONG_PTR = ctypes.c_size_t

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("u",)
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    event = INPUT(
        type=INPUT_MOUSE,
        mi=MOUSEINPUT(0, 0, 0, flag, 0, 0),
    )
    sent = int(user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT)))
    if sent == 1:
        return True

    # Compatibility fallback.
    user32.mouse_event(flag, 0, 0, 0, 0)
    return True


def cursor_position():
    _require_windows()
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    point = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(point)):
        raise ComputerV2Error("Não consegui ler a posição atual do cursor.")
    return int(point.x), int(point.y)


def click_physical(x, y, *, double=False, pause=0.08):
    """Send real mouse input at screen coordinates and verify cursor placement."""
    _require_windows()
    import ctypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    wanted = (int(x), int(y))

    with per_monitor_dpi_v2():
        if not user32.SetCursorPos(*wanted):
            raise ComputerV2Error(
                f"Não consegui mover o mouse para {wanted}."
            )
        time.sleep(max(0.02, float(pause)))
        actual = cursor_position()

        # A few pixels of tolerance is acceptable for Windows pointer snapping.
        if abs(actual[0] - wanted[0]) > 4 or abs(actual[1] - wanted[1]) > 4:
            raise ComputerV2Error(
                f"Cursor não chegou ao ponto solicitado. pedido={wanted}, atual={actual}"
            )

        count = 2 if double else 1
        for index in range(count):
            _send_mouse_button(True)
            time.sleep(0.035)
            _send_mouse_button(False)
            if index + 1 < count:
                time.sleep(0.11)

    return True


def uia_hit_test_chain(x, y, max_ancestors=8):
    """Return the UIA element actually under a screen point plus its ancestors."""
    _require_windows()
    rows = []

    try:
        from pywinauto import Desktop
        ctrl = Desktop(backend="uia").from_point(int(x), int(y))
    except Exception:
        # Low-level fallback documented by Microsoft UI Automation:
        # IUIAutomation.ElementFromPoint.
        try:
            import ctypes
            from ctypes import wintypes
            from pywinauto.windows.uia_defines import IUIA
            from pywinauto.windows.uia_element_info import UIAElementInfo
            from pywinauto.controls.uiawrapper import UIAWrapper

            point = wintypes.POINT(int(x), int(y))
            elem = IUIA().iuia.ElementFromPoint(point)
            ctrl = UIAWrapper(UIAElementInfo(elem))
        except Exception as exc:
            return {
                "ok": False,
                "point": [int(x), int(y)],
                "error": str(exc),
                "chain": [],
            }

    current = ctrl
    for _ in range(max(1, int(max_ancestors))):
        try:
            info = current.element_info
            rect = current.rectangle()
            rows.append({
                "name": str(info.name or "")[:350],
                "automation_id": str(info.automation_id or "")[:180],
                "control_type": str(info.control_type or ""),
                "bounds": [
                    int(rect.left), int(rect.top),
                    int(rect.right), int(rect.bottom),
                ],
            })
            parent = current.parent()
            if parent is None or parent == current:
                break
            current = parent
        except Exception:
            break

    return {
        "ok": bool(rows),
        "point": [int(x), int(y)],
        "chain": rows,
    }


def point_in_bounds(bounds, x_ratio=0.5, y_ratio=0.5, inset=4):
    left, top, right, bottom = [int(v) for v in bounds]
    if right <= left or bottom <= top:
        raise ComputerV2Error("Retângulo de controle inválido.")
    width = right - left
    height = bottom - top
    x = left + int(width * float(x_ratio))
    y = top + int(height * float(y_ratio))
    x = min(max(x, left + inset), right - inset)
    y = min(max(y, top + inset), bottom - inset)
    return x, y


def _open_clipboard(retries=25, delay=0.02):
    import win32clipboard

    last = None
    for _ in range(int(retries)):
        try:
            win32clipboard.OpenClipboard()
            return
        except Exception as exc:
            last = exc
            time.sleep(delay)
    raise ComputerV2Error(f"Clipboard ocupado: {last}")


def clipboard_get_text():
    _require_windows()
    try:
        import win32clipboard
        import win32con
    except Exception as exc:
        raise ComputerV2Error(f"pywin32 necessário para clipboard nativo: {exc}")

    _open_clipboard()
    try:
        try:
            value = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
        except Exception:
            return ""
        return str(value or "")
    finally:
        win32clipboard.CloseClipboard()


def clipboard_set_text(text):
    _require_windows()
    try:
        import win32clipboard
        import win32con
    except Exception as exc:
        raise ComputerV2Error(f"pywin32 necessário para clipboard nativo: {exc}")

    _open_clipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(str(text), win32con.CF_UNICODETEXT)
    finally:
        win32clipboard.CloseClipboard()
    return True


@contextlib.contextmanager
def preserved_clipboard():
    old = ""
    have_old = False
    try:
        old = clipboard_get_text()
        have_old = True
    except Exception:
        pass
    try:
        yield
    finally:
        if have_old:
            try:
                clipboard_set_text(old)
            except Exception:
                pass


def normalize_key_expression(value):
    """Normalize user/model key expressions into pywinauto send_keys syntax."""
    raw = str(value or "").strip().lower()
    raw = raw.replace("control", "ctrl").replace("controle", "ctrl")
    raw = raw.replace("seta para ", "")
    raw = raw.replace("page down", "pagedown").replace("page up", "pageup")
    raw = re.sub(r"\s*\+\s*", "+", raw)

    single = {
        "enter": "{ENTER}", "tab": "{TAB}", "escape": "{ESC}", "esc": "{ESC}",
        "backspace": "{BACKSPACE}", "delete": "{DELETE}", "del": "{DELETE}",
        "up": "{UP}", "cima": "{UP}", "down": "{DOWN}", "baixo": "{DOWN}",
        "left": "{LEFT}", "esquerda": "{LEFT}", "right": "{RIGHT}", "direita": "{RIGHT}",
        "home": "{HOME}", "end": "{END}", "pageup": "{PGUP}", "pagedown": "{PGDN}",
        "space": "{SPACE}", "espaço": "{SPACE}", "espaco": "{SPACE}",
    }
    if raw in single:
        return single[raw]
    if re.fullmatch(r"f(?:[1-9]|1[0-2])", raw):
        return "{" + raw.upper() + "}"

    parts = [p for p in raw.split("+") if p]
    if 2 <= len(parts) <= 4:
        modifiers = {"ctrl": "^", "shift": "+", "alt": "%"}
        prefix = ""
        main = None
        for part in parts:
            if part in modifiers:
                if modifiers[part] not in prefix:
                    prefix += modifiers[part]
            else:
                if main is not None:
                    raise ComputerV2Error("Atalho possui mais de uma tecla principal.")
                main = part
        if not main:
            raise ComputerV2Error("Atalho sem tecla principal.")
        if len(main) == 1 and main.isprintable():
            key = main
        elif main in single:
            key = single[main]
        elif re.fullmatch(r"f(?:[1-9]|1[0-2])", main):
            key = "{" + main.upper() + "}"
        else:
            raise ComputerV2Error(f"Tecla não reconhecida no atalho: {main}")
        return prefix + key

    raise ComputerV2Error(f"Tecla/atalho não reconhecido: {value}")


def send_key_expression(value, *, pause=0.04):
    _require_windows()
    from pywinauto import keyboard

    sequence = normalize_key_expression(value)
    keyboard.send_keys(sequence, pause=float(pause), with_spaces=True)
    return sequence


def paste_unicode(text, *, clear_first=False, hwnd=None):
    """Paste exact Unicode text while restoring the user's clipboard."""
    _require_windows()
    from pywinauto import keyboard

    if hwnd:
        focus_hwnd(hwnd)
    with preserved_clipboard():
        clipboard_set_text(str(text))
        if clear_first:
            keyboard.send_keys("^a", pause=0.03)
        keyboard.send_keys("^v", pause=0.03)
        time.sleep(0.08)
    return True


def copy_focused_text(*, hwnd=None, select_all=True, collapse=True):
    """Read text from the focused editable surface through the clipboard.

    The clipboard is restored. This function never presses Enter and never sends.
    """
    _require_windows()
    from pywinauto import keyboard

    if hwnd:
        focus_hwnd(hwnd)
    sentinel = f"__JARVIS_CLIP_SENTINEL_{uuid.uuid4().hex}__"
    with preserved_clipboard():
        clipboard_set_text(sentinel)
        if select_all:
            keyboard.send_keys("^a", pause=0.03)
        keyboard.send_keys("^c", pause=0.03)
        time.sleep(0.10)
        copied = clipboard_get_text()
        if collapse:
            keyboard.send_keys("{END}", pause=0.02)
    if copied == sentinel:
        return ""
    return copied


def visible_area(bounds):
    if not bounds or len(bounds) != 4:
        return 0
    left, top, right, bottom = bounds
    return max(0, int(right) - int(left)) * max(0, int(bottom) - int(top))
