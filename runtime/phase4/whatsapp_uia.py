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


def _candidate_area(row):
    bounds = row.get("bounds") or [0, 0, 0, 0]
    return max(0, bounds[2] - bounds[0]) * max(0, bounds[3] - bounds[1])


def _static_window_score(row):
    """Rank plausible WhatsApp shells without trusting IsWindowVisible.

    WinUI 3 / WebView2 can render a window that pywinauto/Win32 reports as
    invisible or layered-alpha-zero. Those flags are retained for diagnostics
    but are no longer absolute rejection criteria.
    """
    area = _candidate_area(row)
    if area < 10000:
        return -1

    title = fold(row.get("title", ""))
    exe = str(row.get("exe") or "").casefold()
    cls = str(row.get("class_name") or "").casefold()

    helper_markers = (
        "default ime",
        "msctfime",
        "gdi+ hook",
        "notifyicon",
        "broadcast",
        "crashpad",
        "powermessagewindow",
    )
    if any(marker in (title + " " + cls) for marker in helper_markers):
        return -1

    score = 0

    # Current Microsoft Store shell observed on the test machine.
    if exe == "whatsapp.root.exe" and "winuidesktopwin32windowclass" in cls:
        score += 320
    if exe == WEBVIEW_EXE and "chrome_widgetwin_1" in cls:
        score += 260

    if "whatsapp" in title:
        score += 180
    if exe in WHATSAPP_EXES or exe.startswith("whatsapp."):
        score += 130
    if exe == WEBVIEW_EXE:
        score += 90

    # These are hints only; never hard filters on WinUI/WebView2.
    if row.get("visible"):
        score += 30
    if row.get("foreground"):
        score += 35
    if row.get("alpha_zero"):
        score -= 10

    score += min(area // 50000, 30)
    return score


def choose_window_candidate(rows):
    """Pure ranking used after optional accessibility probing.

    Layered/alpha-zero WebView helpers are accepted only when an actual UIA probe
    proves they expose a useful accessibility tree. This preserves support for
    WhatsApp's real Chrome_WidgetWin_1 while rejecting opaque helper guesses.
    """
    usable = []
    for row in rows:
        score = _static_window_score(row)
        if score < 0:
            continue

        access = int(row.get("accessibility_score") or 0)
        uia_ok = bool(row.get("uia_ok"))

        if row.get("alpha_zero") and not (uia_ok and access > 0):
            continue

        area = _candidate_area(row)
        usable.append((access, score, area, -int(row.get("hwnd") or 0), row))

    if not usable:
        return None
    usable.sort(reverse=True, key=lambda x: (x[0], x[1], x[2], x[3]))
    return usable[0][4]


def _probe_candidate_uia(hwnd):
    """Read-only UIA richness probe for a candidate HWND."""
    from pywinauto import Desktop

    result = {
        "uia_ok": False,
        "uia_descendants": 0,
        "uia_named": 0,
        "uia_fields": 0,
        "uia_buttons": 0,
        "uia_whatsapp_hits": 0,
        "accessibility_score": 0,
        "uia_error": "",
    }

    try:
        win = Desktop(backend="uia").window(handle=int(hwnd))
        # Do not call is_visible(); that is exactly the unreliable signal.
        descendants = win.descendants()
        result["uia_ok"] = True
        result["uia_descendants"] = len(descendants)

        for ctrl in descendants[:4000]:
            try:
                info = ctrl.element_info
                name = str(info.name or "")
                ctype = str(info.control_type or "")
                normalized = fold(name)

                if name.strip():
                    result["uia_named"] += 1
                if ctype in ("Edit", "Document"):
                    result["uia_fields"] += 1
                if ctype == "Button":
                    result["uia_buttons"] += 1
                if any(token in normalized for token in (
                    "whatsapp",
                    "conversas",
                    "pesquisar",
                    "mensagem",
                    "message",
                )):
                    result["uia_whatsapp_hits"] += 1
            except Exception:
                continue

        # Accessibility richness outranks unreliable visibility flags.
        result["accessibility_score"] = (
            min(result["uia_descendants"], 800)
            + result["uia_named"] * 2
            + result["uia_fields"] * 180
            + result["uia_buttons"] * 5
            + result["uia_whatsapp_hits"] * 120
        )
    except Exception as exc:
        result["uia_error"] = str(exc)[:300]

    return result


def _focus_native_hwnd(hwnd):
    """Best-effort foreground activation without relying on pywinauto visibility."""
    if os.name != "nt":
        return False

    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    SW_RESTORE = 9
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL

    try:
        user32.ShowWindow(int(hwnd), SW_RESTORE)
        user32.BringWindowToTop(int(hwnd))
        return bool(user32.SetForegroundWindow(int(hwnd)))
    except Exception:
        return False



CONTACT_CONTAINER_TYPES = {
    "ListItem", "DataItem", "Button", "Hyperlink", "Group", "Custom", "Pane"
}


def _rect_area(bounds):
    bounds = bounds or [0, 0, 0, 0]
    return max(0, bounds[2] - bounds[0]) * max(0, bounds[3] - bounds[1])


def _inside_search_results(row, search_bounds):
    """Restrict matches to the left/search results region below the search box."""
    rect = row.get("bounds") or [0, 0, 0, 0]
    search = search_bounds or [0, 0, 0, 0]
    if _rect_area(rect) <= 0:
        return False
    if rect[1] < search[3] - 4:
        return False
    if rect[0] > search[2] + 80:
        return False
    height = rect[3] - rect[1]
    width = rect[2] - rect[0]
    search_width = max(1, search[2] - search[0])
    if height > 220 or width > max(search_width * 1.45, 720):
        return False
    return True


_RESULT_METADATA_PREFIX = re.compile(
    r"^(?:"
    r"\d{1,2}:\d{2}"
    r"|\d{1,2}/\d{1,2}(?:/\d{2,4})?"
    r"|hoje\b|ontem\b"
    r"|segunda(?:-feira)?\b|terca(?:-feira)?\b|quarta(?:-feira)?\b"
    r"|quinta(?:-feira)?\b|sexta(?:-feira)?\b|sabado\b|domingo\b"
    r")",
    re.I,
)


def contact_accessible_name_matches(name, contact):
    """Strict match for a WhatsApp row name that appends timestamp/date metadata."""
    candidate = identity(name)
    wanted = identity(contact)
    if not candidate or not wanted:
        return False
    if candidate == wanted:
        return True
    if not candidate.startswith(wanted):
        return False
    suffix = candidate[len(wanted):]
    if not suffix or not suffix[0].isspace():
        return False
    tail = fold(suffix.strip())
    return bool(_RESULT_METADATA_PREFIX.match(tail))


def contact_row_matches(row, contact, search_bounds):
    """Strict result-label matcher; never fuzzy-matches another contact name."""
    if not row.get("visible") or not row.get("enabled"):
        return False
    if not _inside_search_results(row, search_bounds):
        return False
    return contact_accessible_name_matches(row.get("name", ""), contact)


def _runtime_id(ctrl):
    try:
        rid = tuple(ctrl.element_info.runtime_id or ())
        if rid:
            return ("rid", rid)
    except Exception:
        pass
    try:
        return ("handle", int(ctrl.handle))
    except Exception:
        return ("obj", id(ctrl))


def _actionable_contact_ancestor(ctrl, win, search_bounds):
    """Climb from an exact Text label to the nearest compact clickable row."""
    current = ctrl
    for _ in range(6):
        try:
            info = current.element_info
            ctype = str(info.control_type or "")
            rect = current.rectangle()
            row = {
                "bounds": [rect.left, rect.top, rect.right, rect.bottom],
                "visible": bool(current.is_visible()),
                "enabled": bool(current.is_enabled()),
            }
            if (
                ctype in CONTACT_CONTAINER_TYPES
                and row["visible"]
                and row["enabled"]
                and _inside_search_results(row, search_bounds)
            ):
                return current
            parent = current.parent()
            if parent is None or parent == current or parent == win:
                break
            current = parent
        except Exception:
            break
    try:
        rect = ctrl.rectangle()
        fallback = {
            "bounds": [rect.left, rect.top, rect.right, rect.bottom],
            "visible": bool(ctrl.is_visible()),
            "enabled": bool(ctrl.is_enabled()),
        }
        if fallback["visible"] and fallback["enabled"] and _inside_search_results(fallback, search_bounds):
            return ctrl
    except Exception:
        pass
    return None


def _control_has_pattern(ctrl, pattern_name):
    try:
        getattr(ctrl, pattern_name)
        return True
    except Exception:
        return False


def _inside_search_results_grid(ctrl):
    current = ctrl
    for _ in range(8):
        try:
            info = current.element_info
            if str(info.control_type or "") == "DataGrid":
                label = fold(info.name or "").strip()
                if "resultados da pesquisa" in label or "search results" in label:
                    return True
            parent = current.parent()
            if parent is None or parent == current:
                break
            current = parent
        except Exception:
            break
    return False


def _contact_candidate_chain(ctrl, win, contact, search_bounds):
    result = []
    current = ctrl
    for depth in range(8):
        try:
            info = current.element_info
            ctype = str(info.control_type or "")
            rect = current.rectangle()
            row = {
                "bounds": [rect.left, rect.top, rect.right, rect.bottom],
                "visible": bool(current.is_visible()),
                "enabled": bool(current.is_enabled()),
            }
            name = str(info.name or "")
            if (
                ctype in CONTACT_CONTAINER_TYPES
                and row["visible"] and row["enabled"]
                and _inside_search_results(row, search_bounds)
                and contact_accessible_name_matches(name, contact)
                and (identity(name) == identity(contact) or _inside_search_results_grid(current))
            ):
                result.append({
                    "ctrl": current,
                    "depth": depth,
                    "area": _rect_area(row["bounds"]),
                    "selection": _control_has_pattern(current, "iface_selection_item"),
                    "invoke": _control_has_pattern(current, "iface_invoke"),
                    "name": name,
                    "control_type": ctype,
                    "bounds": row["bounds"],
                })
            parent = current.parent()
            if parent is None or parent == current or parent == win:
                break
            current = parent
        except Exception:
            break
    return result


def _rank_contact_candidate(item):
    bounds = item.get("bounds") or [0,0,0,0]
    width=max(0,bounds[2]-bounds[0]); height=max(0,bounds[3]-bounds[1])
    return (
        1 if item.get("selection") else 0,
        1 if item.get("control_type") == "DataItem" else 0,
        1 if item.get("invoke") else 0,
        width, height, item.get("area",0), -item.get("depth",0),
    )


def _same_visual_result(a, b):
    aa=a.get("bounds") or [0,0,0,0]; bb=b.get("bounds") or [0,0,0,0]
    return all(abs(x-y) <= 8 for x,y in zip(aa,bb))


def _preferred_activation_node(root, contact):
    """Prefer the nested title/time SelectionItem over the giant preview row."""
    options = []
    try:
        nodes = [root] + list(root.descendants())
    except Exception:
        nodes = [root]

    for ctrl in nodes[:200]:
        try:
            info = ctrl.element_info
            if str(info.control_type or "") != "DataItem":
                continue
            name = str(info.name or "")
            if not contact_accessible_name_matches(name, contact):
                continue
            if not _control_has_pattern(ctrl, "iface_selection_item"):
                continue
            if not ctrl.is_visible() or not ctrl.is_enabled():
                continue
            rect = ctrl.rectangle()
            area = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
            options.append((len(identity(name)), area, ctrl))
        except Exception:
            continue

    if not options:
        return root
    options.sort(key=lambda item: (item[0], item[1]))
    return options[0][2]


def discover_contact_targets(rows, wrappers, win, contact, search_bounds):
    """Resolve one logical result row without fuzzy recipient matching."""
    candidates = []

    for row in rows:
        if not contact_row_matches(row, contact, search_bounds):
            continue
        ctrl = wrappers.get(row.get("key"))
        if ctrl is None:
            continue
        candidates.extend(_contact_candidate_chain(ctrl, win, contact, search_bounds))

        if identity(row.get("name", "")) == identity(contact):
            legacy = _actionable_contact_ancestor(ctrl, win, search_bounds)
            if legacy is not None:
                try:
                    info=legacy.element_info; rect=legacy.rectangle()
                    candidates.append({
                        "ctrl": legacy, "depth":0,
                        "area": max(0,rect.right-rect.left)*max(0,rect.bottom-rect.top),
                        "selection": _control_has_pattern(legacy,"iface_selection_item"),
                        "invoke": _control_has_pattern(legacy,"iface_invoke"),
                        "name": str(info.name or ""),
                        "control_type": str(info.control_type or ""),
                        "bounds": [rect.left,rect.top,rect.right,rect.bottom],
                    })
                except Exception:
                    pass

    # Current WebView2 often exposes only DataItem names, not exact Text children.
    for row in rows:
        if row.get("control_type") not in CONTACT_CONTAINER_TYPES:
            continue
        if not row.get("visible") or not row.get("enabled"):
            continue
        if not _inside_search_results(row, search_bounds):
            continue
        if not contact_accessible_name_matches(row.get("name", ""), contact):
            continue
        ctrl = wrappers.get(row.get("key"))
        if ctrl is None:
            continue
        if identity(row.get("name", "")) != identity(contact) and not _inside_search_results_grid(ctrl):
            continue
        candidates.extend(_contact_candidate_chain(ctrl, win, contact, search_bounds))

    # Runtime-ID dedupe.
    runtime_unique = {}
    for item in candidates:
        marker = _runtime_id(item["ctrl"])
        prev = runtime_unique.get(marker)
        if prev is None or _rank_contact_candidate(item) > _rank_contact_candidate(prev):
            runtime_unique[marker]=item

    ranked = sorted(runtime_unique.values(), key=_rank_contact_candidate, reverse=True)
    if not ranked:
        return []

    best = ranked[0]
    # Treat nested/duplicate WebView2 nodes covering the same row as one result.
    distinct = [x for x in ranked[1:] if not _same_visual_result(best,x)]
    if distinct and _rank_contact_candidate(distinct[0]) == _rank_contact_candidate(best):
        return []
    return [_preferred_activation_node(best["ctrl"], contact)]


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

    # Probe only plausible, non-trivial shells. This is read-only and avoids
    # trusting IsWindowVisible/alpha on WinUI 3 + WebView2.
    plausible = [row for row in rows if _static_window_score(row) >= 0]
    plausible.sort(
        key=lambda row: (_static_window_score(row), _candidate_area(row)),
        reverse=True,
    )
    for row in plausible[:6]:
        row.update(_probe_candidate_uia(row["hwnd"]))

    chosen = choose_window_candidate(rows)
    return {
        "ok": bool(chosen and chosen.get("uia_ok")),
        "roots": sorted(roots),
        "tree_pids": sorted(tree),
        "candidates": rows,
        "chosen": chosen,
        "error": None if chosen and chosen.get("uia_ok") else (
            "Encontrei a árvore do WhatsApp, mas nenhum HWND candidato expôs "
            "uma árvore UI Automation utilizável."
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
        self.contact_names = {}
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
        _focus_native_hwnd(hwnd)
        win = Desktop(backend="uia").window(handle=hwnd)

        # A successful accessibility probe is stronger evidence than
        # WindowSpecification.exists()/is_visible() for this WinUI/WebView2 app.
        if not chosen.get("uia_ok"):
            raise RuntimeError(
                "O HWND candidato do WhatsApp não expôs uma árvore UIA utilizável."
            )

        self.window = win
        self.window_metadata = dict(chosen)
        return win

    def open(self):
        if os.name != "nt":
            raise RuntimeError("Execução desktop disponível somente no Windows.")

        try:
            win = self._attach()
            _focus_native_hwnd(self.window_metadata.get("hwnd"))
            try:
                win.set_focus()
            except Exception:
                pass
            return
        except Exception:
            os.startfile("whatsapp:")

        deadline = time.monotonic() + 8.0
        last_error = None
        while time.monotonic() < deadline:
            try:
                win = self._attach()
                _focus_native_hwnd(self.window_metadata.get("hwnd"))
                try:
                    win.set_focus()
                except Exception:
                    pass
                return
            except Exception as exc:
                last_error = exc
                time.sleep(0.25)
        raise RuntimeError(f"WhatsApp abriu, mas a interface WebView2 não ficou acessível: {last_error}")

    def probe_controls(self):
        """Read-only structural probe for composer discovery.

        Returns metadata only (names/types/ids/bounds/pattern support), never field
        values or chat-history text bodies.
        """
        try:
            win = self._attach()
            wr = win.rectangle()
            rows = []
            descendants = win.descendants()
            window_height = max(1, wr.bottom - wr.top)
            bottom_threshold = wr.top + int(window_height * 0.58)

            for index, ctrl in enumerate(descendants[:4000]):
                try:
                    info = ctrl.element_info
                    rect = ctrl.rectangle()
                    bounds = [rect.left, rect.top, rect.right, rect.bottom]
                    area = max(0, rect.right - rect.left) * max(0, rect.bottom - rect.top)
                    if area <= 0:
                        continue

                    name = str(info.name or "")
                    automation_id = str(info.automation_id or "")
                    ctype = str(info.control_type or "")
                    label = fold(name + " " + automation_id)

                    composer_hint = any(token in label for token in (
                        "mensagem", "message", "compose", "textbox", "input",
                        "editor", "contenteditable", "digite", "type a"
                    ))
                    near_bottom = rect.top >= bottom_threshold

                    # Keep the output compact: likely interactive controls or
                    # anything in the lower part of the WhatsApp content pane.
                    if not (
                        composer_hint
                        or near_bottom
                        or ctype in ("Edit", "Document", "Custom", "Group", "Pane")
                    ):
                        continue

                    patterns = []
                    for attr, label_name in (
                        ("iface_value", "Value"),
                        ("iface_text", "Text"),
                        ("iface_invoke", "Invoke"),
                        ("iface_legacy_iaccessible", "LegacyIAccessible"),
                    ):
                        try:
                            getattr(ctrl, attr)
                            patterns.append(label_name)
                        except Exception:
                            pass

                    try:
                        enabled = bool(ctrl.is_enabled())
                    except Exception:
                        enabled = False
                    try:
                        visible = bool(ctrl.is_visible())
                    except Exception:
                        visible = False
                    try:
                        focused = bool(ctrl.has_keyboard_focus())
                    except Exception:
                        focused = False

                    rows.append({
                        "key": f"control:{index}",
                        "name": name[:180],
                        "automation_id": automation_id[:180],
                        "control_type": ctype,
                        "visible": visible,
                        "enabled": enabled,
                        "focused": focused,
                        "bounds": bounds,
                        "near_bottom": near_bottom,
                        "composer_hint": composer_hint,
                        "patterns": patterns,
                    })
                except Exception:
                    continue

            rows.sort(
                key=lambda item: (
                    not item["composer_hint"],
                    not item["near_bottom"],
                    item["bounds"][1],
                    item["bounds"][0],
                )
            )
            return {
                "ok": True,
                "window": self.window_metadata,
                "descendants": len(descendants),
                "controls": rows[:250],
            }
        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
                "diagnostic": self.diagnose(),
                "controls": [],
            }

    def probe_fields(self):
        """Read-only accessibility probe. Does not expose field values or chat history."""
        try:
            win = self._attach()
            rows = []
            descendants = win.descendants()
            for index, ctrl in enumerate(descendants[:4000]):
                try:
                    item = describe_control(ctrl, f"probe:{index}")
                    if item["control_type"] in ("Edit", "Document"):
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
            self.contact_names = {}
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
                targets = discover_contact_targets(
                    rows, wrappers, win, contact, search_rect
                )
                for target in targets:
                    key = f"{self.generation}:contact:{len(result['contacts'])}"
                    self.controls[key] = target
                    self.contact_names[key] = contact
                    result["contacts"].append({
                        "name": contact,
                        "key": key,
                        "control_type": str(target.element_info.control_type or ""),
                    })
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

    def _conversation_header_present(self, contact):
        """Verify the requested contact is visible as the right-pane header."""
        if not contact:
            return False
        try:
            win = self._attach()
            wr = win.rectangle()
            divider_x = wr.left + int((wr.right - wr.left) * 0.45)

            for ctrl in win.descendants()[:2500]:
                try:
                    info = ctrl.element_info
                    if identity(info.name or "") != identity(contact):
                        continue
                    rect = ctrl.rectangle()
                    center_x = (rect.left + rect.right) / 2
                    if center_x <= divider_x:
                        continue
                    if rect.top > wr.top + int((wr.bottom - wr.top) * 0.35):
                        continue
                    if ctrl.is_visible():
                        return True
                except Exception:
                    continue
        except Exception:
            return False
        return False

    def _wait_conversation_header(self, contact, timeout=1.5):
        deadline = time.monotonic() + max(0.05, float(timeout))
        while time.monotonic() < deadline:
            if self._conversation_header_present(contact):
                return True
            time.sleep(0.10)
        return self._conversation_header_present(contact)

    def _matching_row_rects(self, target, contact):
        """Return nested and outer matching DataItem rectangles, smallest first."""
        rows = []
        current = target
        seen = set()

        for _ in range(10):
            try:
                info = current.element_info
                ctype = str(info.control_type or "")
                name = str(info.name or "")
                rect = current.rectangle()
                bounds = (rect.left, rect.top, rect.right, rect.bottom)

                if (
                    ctype == "DataItem"
                    and contact_accessible_name_matches(name, contact)
                    and bounds not in seen
                    and rect.right > rect.left
                    and rect.bottom > rect.top
                ):
                    seen.add(bounds)
                    rows.append(bounds)

                parent = current.parent()
                if parent is None or parent == current:
                    break
                current = parent
            except Exception:
                break

        rows.sort(
            key=lambda b: (
                max(0, b[2] - b[0]) * max(0, b[3] - b[1])
            )
        )
        return rows

    @staticmethod
    def _safe_row_point(bounds, variant=0):
        """Choose a point inside the text area of a result row.

        Points are derived from live UIA bounds; there are no fixed screen
        coordinates. Avoid the far-right timestamp/pin area.
        """
        left, top, right, bottom = bounds
        width = max(1, right - left)
        height = max(1, bottom - top)

        if variant == 0:
            x = left + int(width * 0.45)
            y = top + int(height * 0.50)
        else:
            x = left + int(width * 0.58)
            y = top + int(height * 0.45)

        x = min(max(x, left + 3), right - 3)
        y = min(max(y, top + 3), bottom - 3)
        return int(x), int(y)

    def _physical_click_point(self, point, double=False):
        """Human-like mouse activation at a live UIA-derived point."""
        if os.name != "nt":
            raise RuntimeError("Ativação física do WhatsApp exige Windows.")

        from pywinauto import mouse

        hwnd = int((self.window_metadata or {}).get("hwnd") or 0)
        if hwnd:
            _focus_native_hwnd(hwnd)
        time.sleep(0.08)

        if double:
            mouse.double_click(button="left", coords=point, interval=0.10)
        else:
            mouse.click(button="left", coords=point)

    def _reacquire_contact_target(self, contact, timeout=5.0):
        """Re-search the contact and return a fresh wrapper after DOM/UI changes."""
        deadline = time.monotonic() + max(0.5, float(timeout))
        last_error = None

        while time.monotonic() < deadline:
            try:
                snap = self.observe(contact, "__jarvis_phase4_reacquire__")
                if not snap.get("ok"):
                    last_error = snap.get("error") or "snapshot inválido"
                    time.sleep(0.15)
                    continue

                if self._conversation_header_present(contact):
                    return None

                search = choose_text_field(snap.get("controls", []), purpose="search")
                if snap.get("search_value") != contact:
                    self.set_text(search["key"], contact)
                    time.sleep(0.20)
                    continue

                matches = [
                    item for item in snap.get("contacts", [])
                    if identity(item.get("name")) == identity(contact)
                ]
                if len(matches) == 1:
                    key = matches[0]["key"]
                    target = self.controls.get(key)
                    if target is not None and target.is_visible() and target.is_enabled():
                        return target

                last_error = "resultado exato ainda não ficou único"
            except Exception as exc:
                last_error = str(exc)
            time.sleep(0.15)

        raise RuntimeError(
            "Não consegui readquirir o resultado exato do WhatsApp após a "
            f"mudança da interface: {last_error or 'tempo esgotado'}."
        )

    def _try_physical_row_activation(self, target, contact, double=False, variant=0):
        rects = self._matching_row_rects(target, contact)
        if not rects:
            try:
                rect = target.rectangle()
                rects = [(rect.left, rect.top, rect.right, rect.bottom)]
            except Exception:
                return False

        # First use the most specific title/time row; then the widest matching row.
        candidates = [rects[0]]
        if len(rects) > 1 and rects[-1] != rects[0]:
            candidates.append(rects[-1])

        for bounds in candidates:
            point = self._safe_row_point(bounds, variant=variant)
            self._physical_click_point(point, double=double)
            if self._wait_conversation_header(contact):
                return True

            # Do not reuse stale geometry after a DOM transition.
            break

        return False

    def open_contact(self, key):
        target = self._target(key)
        contact = self.contact_names.get(key, "")
        if not contact:
            raise RuntimeError("Contato associado ao resultado UIA foi perdido.")

        if self._conversation_header_present(contact):
            return

        # Attempt 1: one human-like physical click on the freshly discovered row.
        if self._try_physical_row_activation(
            target, contact, double=False, variant=0
        ):
            return

        # The first click may mutate/clear the search DOM. Never reuse its wrapper.
        target = self._reacquire_contact_target(contact)
        if target is None and self._conversation_header_present(contact):
            return

        # Attempt 2: a second single click using fresh geometry and a different
        # point inside the row's text area.
        if self._try_physical_row_activation(
            target, contact, double=False, variant=1
        ):
            return

        target = self._reacquire_contact_target(contact)
        if target is None and self._conversation_header_present(contact):
            return

        # Attempt 3: verified double click on a newly acquired row.
        if self._try_physical_row_activation(
            target, contact, double=True, variant=0
        ):
            return

        # Compatibility-only fallback. It is used only if the fresh target
        # actually exposes Invoke, and still requires right-pane verification.
        target = self._reacquire_contact_target(contact)
        if target is None and self._conversation_header_present(contact):
            return
        try:
            target.iface_invoke.Invoke()
            if self._wait_conversation_header(contact):
                return
        except Exception:
            pass

        raise RuntimeError(
            "Localizei e readquiri o resultado correto do WhatsApp, mas nenhuma "
            "ativação física verificada abriu a conversa no painel direito."
        )

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
