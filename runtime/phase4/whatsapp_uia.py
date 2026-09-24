"""Windows WhatsApp Desktop UI Automation adapter.

Supports both the older native executable layout and the current Microsoft Store
package in which WhatsApp.Root.exe hosts the visible UI in WebView2 child
processes. No OCR, fixed coordinates or browser fallback are used.
"""
import ctypes
import os
import re
import time
from pathlib import PureWindowsPath

from .controls import choose_text_field, describe_control
from .intent import fold, identity

PACKAGE_MARKER = "5319275a.whatsappdesktop"
WHATSAPP_EXES = {"whatsapp.exe", "whatsapp.root.exe"}
WEBVIEW_EXE = "msedgewebview2.exe"


def process_image_path(pid):
    """Return executable path using PROCESS_QUERY_LIMITED_INFORMATION."""
    if os.name != "nt":
        return ""
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    handle = kernel32.OpenProcess(0x1000, False, int(pid))
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(32768)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(handle)


def process_basename(pid):
    path = process_image_path(pid)
    return PureWindowsPath(path).name.casefold() if path else ""


def process_snapshot():
    """Return {pid: {pid, ppid, exe, path}} using Toolhelp32; no extra dependency."""
    if os.name != "nt":
        return {}

    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
    MAX_PATH = 260
    ULONG_PTR = ctypes.c_size_t

    class PROCESSENTRY32W(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ULONG_PTR),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", wintypes.WCHAR * MAX_PATH),
        ]

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32FirstW.restype = wintypes.BOOL
    kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
    kernel32.Process32NextW.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE_VALUE:
        return {}

    result = {}
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = kernel32.Process32FirstW(snap, ctypes.byref(entry))
        while ok:
            pid = int(entry.th32ProcessID)
            exe = str(entry.szExeFile or "").casefold()
            result[pid] = {
                "pid": pid,
                "ppid": int(entry.th32ParentProcessID),
                "exe": exe,
                "path": "",
            }
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
            ok = kernel32.Process32NextW(snap, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snap)

    # Query paths only for WhatsApp roots and likely descendants on demand later.
    return result


def descendant_pids(processes, root_ids):
    """Pure helper used by runtime and tests."""
    found = {int(x) for x in root_ids}
    changed = True
    while changed:
        changed = False
        for pid, row in processes.items():
            if int(row.get("ppid", -1)) in found and int(pid) not in found:
                found.add(int(pid))
                changed = True
    return found


def _whatsapp_process_tree():
    processes = process_snapshot()
    roots = set()

    for pid, row in processes.items():
        exe = str(row.get("exe") or "").casefold()
        if exe in WHATSAPP_EXES or exe.startswith("whatsapp."):
            roots.add(int(pid))

    # If Toolhelp names are unusual, check running process paths too.
    if not roots:
        for pid, row in processes.items():
            path = process_image_path(pid)
            if path and PACKAGE_MARKER in path.casefold():
                row["path"] = path
                roots.add(int(pid))

    pids = descendant_pids(processes, roots)

    # Fill paths only for the small candidate tree.
    for pid in list(pids):
        row = processes.get(pid)
        if row is not None and not row.get("path"):
            row["path"] = process_image_path(pid)

    return processes, roots, pids


def _window_alpha_zero(hwnd):
    """Reject invisible transparent WebView2 helper windows."""
    if os.name != "nt":
        return False
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    LWA_ALPHA = 0x00000002

    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    style = int(user32.GetWindowLongW(int(hwnd), GWL_EXSTYLE))
    if not (style & WS_EX_LAYERED):
        return False

    color = wintypes.DWORD()
    alpha = ctypes.c_ubyte()
    flags = wintypes.DWORD()
    user32.GetLayeredWindowAttributes.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.POINTER(ctypes.c_ubyte),
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetLayeredWindowAttributes.restype = wintypes.BOOL
    ok = user32.GetLayeredWindowAttributes(
        int(hwnd), ctypes.byref(color), ctypes.byref(alpha), ctypes.byref(flags)
    )
    return bool(ok and (flags.value & LWA_ALPHA) and alpha.value == 0)


def choose_window_candidate(rows):
    """Pure deterministic ranking; returns None when no usable native UI exists."""
    usable = []
    for row in rows:
        if not row.get("visible") or row.get("alpha_zero"):
            continue
        bounds = row.get("bounds") or [0, 0, 0, 0]
        area = max(0, bounds[2] - bounds[0]) * max(0, bounds[3] - bounds[1])
        if area < 10000:
            continue

        title = fold(row.get("title", ""))
        exe = str(row.get("exe") or "").casefold()
        cls = str(row.get("class_name") or "").casefold()

        score = 0
        if "whatsapp" in title:
            score += 120
        if exe in WHATSAPP_EXES or exe.startswith("whatsapp."):
            score += 100
        if exe == WEBVIEW_EXE:
            score += 80
        if "chrome_widgetwin" in cls:
            score += 35
        if row.get("foreground"):
            score += 25

        # Larger normal windows beat tiny helpers but area cannot dominate identity.
        score += min(area // 50000, 25)
        usable.append((score, area, -int(row.get("hwnd") or 0), row))

    if not usable:
        return None
    usable.sort(reverse=True, key=lambda x: (x[0], x[1], x[2]))
    return usable[0][3]


def discover_whatsapp_windows():
    """Discover native WhatsApp windows including WebView2 child-process hosts."""
    if os.name != "nt":
        return {"ok": False, "error": "Windows necessário.", "candidates": [], "chosen": None}

    from pywinauto import Desktop
    from ctypes import wintypes

    processes, roots, tree = _whatsapp_process_tree()
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetForegroundWindow.restype = wintypes.HWND
    foreground = int(user32.GetForegroundWindow() or 0)

    rows = []
    try:
        windows = Desktop(backend="win32").windows(visible_only=False)
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Falha ao enumerar janelas Win32: {exc}",
            "roots": sorted(roots),
            "tree_pids": sorted(tree),
            "candidates": [],
            "chosen": None,
        }

    for win in windows:
        try:
            pid = int(win.element_info.process_id)
            if pid not in tree:
                continue
            hwnd = int(win.handle)
            rect = win.rectangle()
            row = processes.get(pid, {})
            exe = str(row.get("exe") or process_basename(pid)).casefold()
            rows.append({
                "hwnd": hwnd,
                "pid": pid,
                "ppid": int(row.get("ppid") or 0),
                "exe": exe,
                "path": row.get("path") or "",
                "title": win.window_text() or "",
                "class_name": win.class_name() or "",
                "visible": bool(win.is_visible()),
                "enabled": bool(win.is_enabled()),
                "foreground": hwnd == foreground,
                "alpha_zero": _window_alpha_zero(hwnd),
                "bounds": [rect.left, rect.top, rect.right, rect.bottom],
            })
        except Exception:
            continue

    chosen = choose_window_candidate(rows)
    return {
        "ok": bool(chosen),
        "roots": sorted(roots),
        "tree_pids": sorted(tree),
        "candidates": rows,
        "chosen": chosen,
        "error": None if chosen else (
            "Encontrei o processo do WhatsApp, mas nenhuma janela utilizável da árvore "
            "WhatsApp.Root/WebView2 ficou disponível."
        ),
    }


def message_evidence(label, automation_id, child_names, message):
    """Positive direction AND positive send state required; fail closed otherwise."""
    normalized = fold(label)
    aid = fold(automation_id)
    outgoing = bool(
        re.search(r"^(?:voce|you)\s*:", normalized)
        or any(x in aid for x in ("outgoingmessage", "sentmessage", "messagemine"))
    )
    body = message in child_names
    if not body:
        body = any(
            label.startswith(prefix + message + separator)
            for prefix in ("Você: ", "You: ", "você: ", "you: ")
            for separator in ("\n", ", ", ". ")
        )
    metadata_label = label.replace(message, "") if message else label
    joined = fold("\n".join([metadata_label] + [x for x in child_names if x != message]))
    if re.search(
        r"\b(?:pending|sending|failed|not sent|nao enviad[ao]|enviando|pendente|falha|retry|tentar novamente)\b",
        joined,
    ):
        state = "pending_or_failed"
    elif re.search(r"\b(?:read|lida|lido)\b", joined):
        state = "read"
    elif re.search(r"\b(?:delivered|entregue)\b", joined):
        state = "delivered"
    elif re.search(r"\b(?:sent|enviada|enviado)\b", joined):
        state = "sent"
    else:
        state = "unknown"
    return {"text": message if body else "", "outgoing": outgoing, "state": state}


class WhatsAppUIA:
    def __init__(self):
        self.window = None
        self.controls = {}
        self.generation = 0
        self.window_metadata = {}

    def diagnose(self):
        return discover_whatsapp_windows()

    def _attach(self):
        if os.name != "nt":
            raise RuntimeError("WhatsApp Desktop UIA exige Windows com sessão gráfica desbloqueada.")

        from pywinauto import Desktop

        discovery = discover_whatsapp_windows()
        chosen = discovery.get("chosen")
        if not chosen:
            roots = discovery.get("roots") or []
            tree = discovery.get("tree_pids") or []
            raise RuntimeError(
                "WhatsApp.Root foi detectado, mas não encontrei a janela WebView2 utilizável. "
                f"roots={roots}, processos_da_arvore={len(tree)}. "
                "Execute run_phase4_tests.py --probe para diagnóstico."
            )

        hwnd = int(chosen["hwnd"])
        win = Desktop(backend="uia").window(handle=hwnd)
        if not win.exists(timeout=1.0):
            raise RuntimeError("A janela WhatsApp descoberta não pôde ser conectada pelo backend UIA.")

        self.window = win
        self.window_metadata = dict(chosen)
        return win

    def open(self):
        if os.name != "nt":
            raise RuntimeError("Execução desktop disponível somente no Windows.")

        try:
            self._attach().set_focus()
            return
        except Exception:
            os.startfile("whatsapp:")

        deadline = time.monotonic() + 8.0
        last_error = None
        while time.monotonic() < deadline:
            try:
                self._attach().set_focus()
                return
            except Exception as exc:
                last_error = exc
                time.sleep(0.25)
        raise RuntimeError(f"WhatsApp abriu, mas a interface WebView2 não ficou acessível: {last_error}")

    def probe_fields(self):
        """Read-only accessibility probe. Does not expose field values or chat history."""
        try:
            win = self._attach()
            rows = []
            descendants = win.descendants()
            for index, ctrl in enumerate(descendants[:4000]):
                try:
                    item = describe_control(ctrl, f"probe:{index}")
                    if item["visible"] and item["control_type"] in ("Edit", "Document"):
                        item = dict(item)
                        item.pop("focused", None)
                        rows.append(item)
                except Exception:
                    continue
            return {
                "ok": True,
                "window": self.window_metadata,
                "descendants": len(descendants),
                "fields": rows,
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "diagnostic": self.diagnose(),
                "fields": [],
            }

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
                    key = f"{self.generation}:{index}"
                    item = describe_control(ctrl, key)
                    if not item["visible"]:
                        continue
                    rows.append(item)
                    wrappers[key] = ctrl
                except Exception:
                    complete = False
            self.controls = wrappers
            result = {
                "ok": True,
                "complete": complete,
                "controls": rows,
                "contacts": [],
                "conversation": "",
                "composer": None,
                "draft": None,
                "search_value": None,
                "messages": [],
            }

            try:
                search = choose_text_field(rows, purpose="search")
                search_rect = search["bounds"]
                result["search_value"] = self._value(wrappers[search["key"]])
                seen = set()
                for row in rows:
                    if row["control_type"] not in ("ListItem", "DataItem") or not row["enabled"]:
                        continue
                    rect = row["bounds"]
                    if rect[0] > search_rect[2] or rect[1] < search_rect[3]:
                        continue
                    ctrl = wrappers[row["key"]]
                    names = [row["name"]] + [
                        c.element_info.name or "" for c in ctrl.descendants(control_type="Text")
                    ]
                    if any(identity(n) == identity(contact) for n in names):
                        rid = tuple(ctrl.element_info.runtime_id or ())
                        if rid and rid not in seen:
                            result["contacts"].append({"name": contact, "key": row["key"]})
                            seen.add(rid)
            except RuntimeError:
                pass

            try:
                composer = choose_text_field(rows, purpose="message")
                result["composer"] = composer["key"]
                result["draft"] = self._value(wrappers[composer["key"]])
                rect = composer["bounds"]
                wr = win.rectangle()
                headers = [
                    r
                    for r in rows
                    if r["control_type"] in ("Text", "Button")
                    and identity(r["name"]) == identity(contact)
                    and r["bounds"][0] >= rect[0] - 30
                    and r["bounds"][1] < wr.top + (wr.bottom - wr.top) * 0.22
                ]
                if len(headers) == 1:
                    result["conversation"] = contact

                seen = set()
                for row in rows:
                    if row["control_type"] not in ("ListItem", "DataItem", "Group"):
                        continue
                    if row["bounds"][0] < rect[0] - 30 or row["bounds"][3] > rect[1]:
                        continue
                    ctrl = wrappers[row["key"]]
                    children = [c.element_info.name or "" for c in ctrl.descendants()]
                    evidence = message_evidence(
                        row["name"], row["automation_id"], children, message
                    )
                    if not evidence["text"]:
                        continue
                    rid = tuple(ctrl.element_info.runtime_id or ())
                    if not rid:
                        complete = False
                        continue
                    if rid not in seen and evidence["outgoing"]:
                        result["messages"].append({"id": repr(rid), **evidence})
                        seen.add(rid)
            except RuntimeError:
                pass

            result["complete"] = complete
            return result
        except Exception as exc:
            return {
                "ok": False,
                "complete": False,
                "error": str(exc),
                "controls": [],
                "messages": [],
            }

    def _target(self, key):
        ctrl = self.controls.get(key)
        if ctrl is None or not ctrl.is_visible() or not ctrl.is_enabled():
            raise RuntimeError("Controle UIA ausente, obsoleto ou desabilitado.")
        self._attach().set_focus()
        return ctrl

    def set_text(self, key, text):
        target = self._target(key)
        choose_text_field([describe_control(target, key)])
        target.set_focus()
        target.iface_value.SetValue(str(text))

    def open_contact(self, key):
        target = self._target(key)
        try:
            invoke = target.iface_invoke
        except Exception:
            target.click_input()
        else:
            invoke.Invoke()

    def send(self, contact, message):
        snap = self.observe(contact, message)
        if (
            identity(snap.get("conversation")) != identity(contact)
            or snap.get("draft") != message
            or not snap.get("complete")
        ):
            raise RuntimeError("Conversa/campo mudou antes de enviar; operação interrompida.")

        composer = choose_text_field(snap["controls"], purpose="message")
        rect = composer["bounds"]
        buttons = [
            c
            for c in snap["controls"]
            if c["control_type"] == "Button"
            and c["enabled"]
            and fold(c["name"]).strip()
            in ("enviar", "send", "enviar mensagem", "send message")
            and c["bounds"][0] >= rect[0]
            and abs(c["bounds"][1] - rect[1]) < 100
        ]
        if len(buttons) != 1:
            raise RuntimeError(
                "Botão Enviar ausente ou ambíguo; não foi usado Enter como alternativa."
            )
        target = self._target(buttons[0]["key"])
        target.iface_invoke.Invoke()
