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
from runtime.computer_v2 import (
    click_physical, copy_focused_text, focus_hwnd, paste_unicode,
    point_in_bounds, send_key_expression, visible_area, uia_hit_test_chain,
)

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


def _safe_uia_bool(fn, default=False):
    try:
        return bool(fn())
    except Exception:
        return default


def _raw_edit_score(ctrl, window_bounds):
    """Score a raw UIA Edit as WhatsApp's global search box.

    Current WhatsApp WebView2 may expose this field with an empty accessible
    name and a generated automation id (observed `_r_f_`). Therefore semantic
    labels are preferred, but geometry + editability are valid evidence.
    """
    try:
        info = ctrl.element_info
        if str(info.control_type or "") != "Edit":
            return -1, None
        rect = ctrl.rectangle()
        bounds = [rect.left, rect.top, rect.right, rect.bottom]
        if visible_area(bounds) <= 20:
            return -1, None

        enabled = _safe_uia_bool(ctrl.is_enabled)
        if not enabled:
            return -1, None

        name = str(info.name or "")
        aid = str(info.automation_id or "")
        label = fold(name + " " + aid)

        read_only = None
        has_value = False
        try:
            value = ctrl.iface_value
            read_only = bool(value.CurrentIsReadOnly)
            has_value = True
        except Exception:
            pass
        if read_only is True:
            return -1, None

        wl, wt, wr, wb = [int(x) for x in window_bounds]
        width = max(1, wr - wl)
        height = max(1, wb - wt)
        cx = (rect.left + rect.right) / 2
        cy = (rect.top + rect.bottom) / 2

        score = 0
        if "pesquisar" in label or "search" in label:
            score += 350
        if "nova conversa" in label or "new chat" in label:
            score += 140

        # This generated id was observed on the user's current WhatsApp build.
        # It is only a hint; geometry/editability still need to agree.
        if aid == "_r_f_":
            score += 180

        # WhatsApp global search is in the upper-left content pane.
        if cx <= wl + width * 0.48:
            score += 120
        if cy <= wt + height * 0.28:
            score += 120
        if rect.left >= wl + width * 0.05:
            score += 20

        if has_value:
            score += 100
        if _safe_uia_bool(ctrl.is_visible):
            score += 20

        return score, {
            "name": name,
            "automation_id": aid,
            "bounds": bounds,
            "read_only": read_only,
            "score": score,
        }
    except Exception:
        return -1, None


def _raw_find_search_control(win):
    wr = win.rectangle()
    window_bounds = [wr.left, wr.top, wr.right, wr.bottom]
    candidates = []

    for index, ctrl in enumerate(win.descendants()[:4000]):
        score, meta = _raw_edit_score(ctrl, window_bounds)
        if score < 0 or meta is None:
            continue
        candidates.append((score, -visible_area(meta["bounds"]), index, ctrl, meta))

    if not candidates:
        return None, None

    candidates.sort(reverse=True, key=lambda row: (row[0], row[1], -row[2]))
    best = candidates[0]

    # Fail closed only for genuinely different equal-strength fields.
    if len(candidates) > 1 and candidates[1][0] == best[0]:
        a = best[4]["bounds"]
        b = candidates[1][4]["bounds"]
        if any(abs(x - y) > 8 for x, y in zip(a, b)):
            return None, None

    return best[3], best[4]


def _raw_read_value(ctrl):
    try:
        return str(ctrl.iface_value.CurrentValue)
    except Exception:
        try:
            return str(ctrl.window_text() or "")
        except Exception:
            return None


def _raw_set_value(ctrl, text):
    """Write to a verified raw Edit and immediately re-read it."""
    target = str(text)
    try:
        ctrl.set_focus()
    except Exception:
        pass

    first_error = None
    try:
        value = ctrl.iface_value
        if bool(value.CurrentIsReadOnly):
            raise RuntimeError("Campo raw UIA está read-only.")
        value.SetValue(target)
        actual = str(value.CurrentValue)
        if actual != target:
            raise RuntimeError(
                f"ValuePattern escreveu valor diferente: {actual!r}"
            )
        return actual
    except Exception as exc:
        first_error = exc

    try:
        ctrl.set_edit_text(target)
        actual = _raw_read_value(ctrl)
        if actual != target:
            raise RuntimeError(
                f"set_edit_text escreveu valor diferente: {actual!r}"
            )
        return actual
    except Exception as second:
        raise RuntimeError(
            "Não consegui escrever no campo raw de pesquisa. "
            f"ValuePattern={first_error}; set_edit_text={second}"
        )


def _raw_has_search_results_ancestor(ctrl):
    current = ctrl
    for _ in range(10):
        try:
            info = current.element_info
            if str(info.control_type or "") == "DataGrid":
                name = fold(info.name or "")
                if "resultados da pesquisa" in name or "search results" in name:
                    return True
            parent = current.parent()
            if parent is None or parent == current:
                break
            current = parent
        except Exception:
            break
    return False


def _raw_contact_rows(win, contact, search_bounds):
    """Return one logical WhatsApp search result using the raw WebView2 tree."""
    wr = win.rectangle()
    window_width = max(1, wr.right - wr.left)
    left_panel_limit = wr.left + int(window_width * 0.52)
    search_bottom = int((search_bounds or [0, 0, 0, wr.top])[3])

    candidates = []
    for index, ctrl in enumerate(win.descendants()[:4000]):
        try:
            info = ctrl.element_info
            if str(info.control_type or "") != "DataItem":
                continue
            name = str(info.name or "")
            if not contact_accessible_name_matches(name, contact):
                continue
            rect = ctrl.rectangle()
            bounds = [rect.left, rect.top, rect.right, rect.bottom]
            if visible_area(bounds) <= 20:
                continue
            if rect.left > left_panel_limit or rect.bottom < search_bottom - 4:
                continue
            if not _safe_uia_bool(ctrl.is_enabled):
                continue

            in_grid = _raw_has_search_results_ancestor(ctrl)
            exact = identity(name) == identity(contact)
            if not (in_grid or exact):
                continue

            selection = _control_has_pattern(ctrl, "iface_selection_item")
            invoke = _control_has_pattern(ctrl, "iface_invoke")
            area = visible_area(bounds)

            # Same contact row is commonly represented by several nested DataItems.
            # Larger row with SelectionItem is the best physical click target.
            score = (
                300 if selection else 0,
                100 if in_grid else 0,
                40 if invoke else 0,
                area,
                -len(identity(name)),
            )
            candidates.append({
                "ctrl": ctrl,
                "index": index,
                "name": name,
                "bounds": bounds,
                "selection": selection,
                "invoke": invoke,
                "in_grid": in_grid,
                "score": score,
            })
        except Exception:
            continue

    if not candidates:
        return []

    # Group nested duplicates by visual row. Their top-left and width are close.
    groups = []
    for item in sorted(candidates, key=lambda x: x["bounds"][1]):
        placed = False
        for group in groups:
            ref = group[0]["bounds"]
            cur = item["bounds"]
            same_row = (
                abs(ref[1] - cur[1]) <= 18
                and abs(ref[3] - cur[3]) <= 45
                and not (cur[2] < ref[0] or cur[0] > ref[2])
            )
            if same_row:
                group.append(item)
                placed = True
                break
        if not placed:
            groups.append([item])

    logical = []
    for group in groups:
        best = max(group, key=lambda x: x["score"])
        logical.append(best)

    # Search result must be unique for the requested identity.
    if len(logical) != 1:
        return []
    return logical


def _raw_header_present(win, contact):
    return bool(_raw_conversation_evidence(win, contact).get("verified"))



def _right_pane_contact_name_matches(name, contact):
    """Header matching is intentionally different from search-row matching."""
    got = identity(name)
    wanted = identity(contact)
    if not got or not wanted:
        return False
    if got == wanted:
        return True
    # Some Chromium accessibility trees append presence/status metadata to the
    # header accessible name. Only allow a short suffix in the RIGHT pane.
    if got.startswith(wanted + " ") and len(got) <= len(wanted) + 80:
        return True
    return False


def _raw_conversation_evidence(win, contact):
    evidence = {
        "verified": False,
        "header": None,
        "neutral_markers": [],
        "right_top_named": [],
    }
    try:
        wr = win.rectangle()
        width = max(1, wr.right - wr.left)
        height = max(1, wr.bottom - wr.top)
        divider = wr.left + width * 0.43
        top_limit = wr.top + height * 0.38

        neutral_terms = (
            "enviar documento",
            "adicionar contato",
            "perguntar a meta ai",
            "perguntar à meta ai",
        )

        for ctrl in win.descendants()[:4000]:
            try:
                info = ctrl.element_info
                name = str(info.name or "").strip()
                if not name:
                    continue
                rect = ctrl.rectangle()
                bounds = [
                    int(rect.left), int(rect.top),
                    int(rect.right), int(rect.bottom),
                ]
                if visible_area(bounds) <= 20:
                    continue
                cx = (rect.left + rect.right) / 2
                if cx <= divider:
                    continue

                low = fold(name)
                if any(term in low for term in neutral_terms):
                    evidence["neutral_markers"].append(name[:180])

                if rect.top <= top_limit:
                    if len(evidence["right_top_named"]) < 80:
                        evidence["right_top_named"].append({
                            "name": name[:220],
                            "control_type": str(info.control_type or ""),
                            "bounds": bounds,
                        })

                    if _right_pane_contact_name_matches(name, contact):
                        evidence["verified"] = True
                        evidence["header"] = {
                            "name": name[:220],
                            "control_type": str(info.control_type or ""),
                            "bounds": bounds,
                        }
                        return evidence
            except Exception:
                continue
    except Exception as exc:
        evidence["error"] = str(exc)

    return evidence


def _hit_chain_matches_contact(hit, contact):
    for row in (hit or {}).get("chain", []):
        name = str(row.get("name") or "")
        if contact_accessible_name_matches(name, contact):
            return True
    return False


def _contact_click_candidates(target, contact):
    """Generate click points from the most specific live matching descendants."""
    items = []
    try:
        nodes = [target] + list(target.descendants())
    except Exception:
        nodes = [target]

    for ctrl in nodes[:300]:
        try:
            info = ctrl.element_info
            name = str(info.name or "")
            if not contact_accessible_name_matches(name, contact):
                continue
            rect = ctrl.rectangle()
            bounds = [
                int(rect.left), int(rect.top),
                int(rect.right), int(rect.bottom),
            ]
            area = visible_area(bounds)
            if area <= 20:
                continue
            exactness = len(identity(name))
            # Specific title/time child first; outer row later.
            items.append((exactness, area, bounds))
        except Exception:
            continue

    try:
        rect = target.rectangle()
        outer = [
            int(rect.left), int(rect.top),
            int(rect.right), int(rect.bottom),
        ]
        if visible_area(outer) > 20:
            items.append((10**9, visible_area(outer), outer))
    except Exception:
        pass

    items.sort(key=lambda row: (row[0], row[1]))

    points = []
    seen = set()
    ratios = ((0.50, 0.50), (0.38, 0.50), (0.62, 0.50))
    for _name_len, _area, bounds in items:
        for xr, yr in ratios:
            try:
                point = point_in_bounds(bounds, xr, yr)
            except Exception:
                continue
            if point not in seen:
                seen.add(point)
                points.append({
                    "point": list(point),
                    "bounds": list(bounds),
                })
    return points[:30]



class WhatsAppUIA:
    def __init__(self):
        self.window = None
        self.controls = {}
        self.contact_names = {}
        self.search_key = None
        self.synthetic_composer_key = None
        self.current_contact_hint = ""
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

    def _synthetic_composer_descriptor(self, win, key):
        wr = win.rectangle()
        width = max(1, wr.right - wr.left)
        height = max(1, wr.bottom - wr.top)
        left = wr.left + int(width * 0.43)
        right = wr.right - max(18, int(width * 0.03))
        bottom = wr.bottom - max(12, int(height * 0.025))
        top = bottom - max(42, int(height * 0.065))
        return {
            "key": key,
            "name": "Digite uma mensagem",
            "automation_id": "__jarvis_keyboard_composer__",
            "control_type": "Edit",
            "visible": True,
            "enabled": True,
            "password": False,
            "read_only": False,
            "focused": False,
            "bounds": [left, top, right, bottom],
            "synthetic": True,
        }

    def _conversation_header_present(self, contact):
        if not contact:
            return False
        try:
            evidence = _raw_conversation_evidence(self._attach(), contact)
            self.last_conversation_evidence = evidence
            return bool(evidence.get("verified"))
        except Exception as exc:
            self.last_conversation_evidence = {
                "verified": False,
                "error": str(exc),
            }
            return False

    def _wait_conversation_header(self, contact, timeout=2.0):
        deadline = time.monotonic() + max(0.05, float(timeout))
        while time.monotonic() < deadline:
            if self._conversation_header_present(contact):
                return True
            time.sleep(0.10)
        return self._conversation_header_present(contact)

    def _focus_whatsapp(self):
        hwnd = int((self.window_metadata or {}).get("hwnd") or 0)
        focused = False
        if hwnd:
            try:
                focused = bool(focus_hwnd(hwnd))
            except Exception:
                focused = False
        try:
            self._attach().set_focus()
        except Exception:
            pass
        return focused

    def _focus_keyboard_composer(self, contact):
        if not self._conversation_header_present(contact):
            raise RuntimeError("A conversa solicitada não está aberta no painel direito.")
        win = self._attach()
        self._focus_whatsapp()
        desc = self._synthetic_composer_descriptor(win, "__probe_composer__")
        point = point_in_bounds(desc["bounds"], 0.55, 0.55)
        click_physical(*point)
        time.sleep(0.10)
        return desc

    def _read_keyboard_composer(self, contact):
        self._focus_keyboard_composer(contact)
        hwnd = int((self.window_metadata or {}).get("hwnd") or 0)
        copied = copy_focused_text(hwnd=hwnd, select_all=True, collapse=True)
        # If focus accidentally landed on a broad page surface, copying tends to
        # return large UI text. Treat that as unverifiable instead of a draft.
        if len(copied) > 12000:
            raise RuntimeError("O foco do compositor não pôde ser verificado com segurança.")
        return copied

    def _write_keyboard_composer(self, contact, text):
        self._focus_keyboard_composer(contact)
        hwnd = int((self.window_metadata or {}).get("hwnd") or 0)
        paste_unicode(str(text), clear_first=True, hwnd=hwnd)
        actual = copy_focused_text(hwnd=hwnd, select_all=True, collapse=True)
        if actual != str(text):
            raise RuntimeError("Digitei no compositor, mas não consegui reler o texto literal exato.")
        return actual

    def observe(self, contact, message):
        self.current_contact_hint = str(contact or "").strip()
        self.generation += 1
        self.controls = {}
        self.contact_names = {}
        self.search_key = None
        self.synthetic_composer_key = None

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
                    if not item["visible"] and visible_area(item.get("bounds")) <= 20:
                        continue
                    rows.append(item)
                    wrappers[key] = ctrl
                except Exception:
                    complete = False

            self.controls = dict(wrappers)
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
                "raw_bridge": True,
            }

            # RAW SEARCH BRIDGE.
            # Do not depend on normalized accessible labels: the user's current
            # WebView2 build exposes the global search Edit with an empty name.
            raw_search, raw_meta = _raw_find_search_control(win)
            search_rect = None
            if raw_search is not None and raw_meta is not None:
                raw_rid = _runtime_id(raw_search)

                # Remove the same raw control from normalized rows so
                # choose_text_field() cannot see duplicate aliases.
                filtered_rows = []
                filtered_wrappers = {}
                for row in rows:
                    ctrl = wrappers.get(row["key"])
                    if ctrl is not None and _runtime_id(ctrl) == raw_rid:
                        continue
                    filtered_rows.append(row)
                    filtered_wrappers[row["key"]] = ctrl

                rows = filtered_rows
                wrappers = filtered_wrappers

                key = f"{self.generation}:search:raw"
                search_desc = {
                    "key": key,
                    "name": raw_meta["name"] or "Pesquisar ou começar uma nova conversa",
                    "automation_id": raw_meta["automation_id"] or "__jarvis_raw_search__",
                    "control_type": "Edit",
                    "visible": True,
                    "enabled": True,
                    "password": False,
                    "read_only": False,
                    "focused": False,
                    "bounds": list(raw_meta["bounds"]),
                    "raw_search": True,
                }
                rows.append(search_desc)
                wrappers[key] = raw_search
                self.controls = dict(wrappers)
                self.search_key = key
                search_rect = search_desc["bounds"]
                result["search_value"] = _raw_read_value(raw_search)

                for item in _raw_contact_rows(win, contact, search_rect):
                    ckey = f"{self.generation}:contact:raw:{len(result['contacts'])}"
                    self.controls[ckey] = item["ctrl"]
                    self.contact_names[ckey] = contact
                    result["contacts"].append({
                        "name": contact,
                        "key": ckey,
                        "control_type": "DataItem",
                        "bounds": list(item["bounds"]),
                        "raw_contact": True,
                    })
            else:
                # Compatibility fallback for older/native builds.
                try:
                    search = choose_text_field(rows, purpose="search")
                    self.search_key = search["key"]
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

            result["controls"] = rows

            if _raw_header_present(win, contact):
                result["conversation"] = contact

            composer_desc = None
            try:
                composer_desc = choose_text_field(rows, purpose="message")
                result["composer"] = composer_desc["key"]
                result["draft"] = self._value(self.controls[composer_desc["key"]])
            except RuntimeError:
                if result["conversation"]:
                    key = f"{self.generation}:composer:keyboard"
                    composer_desc = self._synthetic_composer_descriptor(win, key)
                    rows.append(composer_desc)
                    self.controls[key] = "__keyboard_composer__"
                    self.synthetic_composer_key = key
                    result["composer"] = key
                    try:
                        result["draft"] = self._read_keyboard_composer(contact)
                    except Exception:
                        result["draft"] = None

            # Message-bubble verification remains conservative. Synthetic
            # composer geometry is enough to delimit the conversation region.
            if composer_desc is not None:
                rect = composer_desc["bounds"]
                seen = set()
                for row in rows:
                    if row.get("synthetic") or row.get("raw_search"):
                        continue
                    if row["control_type"] not in ("ListItem", "DataItem", "Group"):
                        continue
                    if row["bounds"][0] < rect[0] - 50 or row["bounds"][3] > rect[1]:
                        continue
                    ctrl = self.controls.get(row["key"])
                    if ctrl in (None, "__keyboard_composer__"):
                        continue
                    try:
                        children = [c.element_info.name or "" for c in ctrl.descendants()]
                    except Exception:
                        children = []
                    evidence = message_evidence(
                        row["name"], row["automation_id"], children, message
                    )
                    if not evidence["text"]:
                        continue
                    try:
                        rid = tuple(ctrl.element_info.runtime_id or ())
                    except Exception:
                        rid = ()
                    if not rid:
                        complete = False
                        continue
                    if rid not in seen and evidence["outgoing"]:
                        result["messages"].append({
                            "id": repr(rid),
                            **evidence,
                        })
                        seen.add(rid)

            result["controls"] = rows
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
        if ctrl is None:
            raise RuntimeError("Controle UIA ausente ou obsoleto.")
        if ctrl == "__keyboard_composer__":
            return ctrl
        if not ctrl.is_enabled():
            raise RuntimeError("Controle UIA desabilitado.")
        try:
            visible = bool(ctrl.is_visible())
        except Exception:
            visible = False
        if not visible:
            try:
                rect = ctrl.rectangle()
                if visible_area([rect.left, rect.top, rect.right, rect.bottom]) <= 20:
                    raise RuntimeError("Controle UIA não está visível.")
            except Exception:
                raise RuntimeError("Controle UIA não está visível.")
        self._focus_whatsapp()
        return ctrl

    def set_text(self, key, text):
        target = self.controls.get(key)

        if target == "__keyboard_composer__":
            contact = self.current_contact_hint
            if not contact:
                candidates = list(dict.fromkeys(self.contact_names.values()))
                if len(candidates) == 1:
                    contact = candidates[0]
            if not contact:
                raise RuntimeError("Não consegui associar o compositor à conversa aberta.")
            self._write_keyboard_composer(contact, str(text))
            return

        target = self._target(key)

        # Raw search bridge: use the exact method that succeeded in the direct
        # diagnostic on this WhatsApp build.
        if key == self.search_key:
            actual = _raw_set_value(target, str(text))
            if actual != str(text):
                raise RuntimeError("A busca raw não pôde ser relida exatamente.")
            return

        row = describe_control(target, key)
        choose_text_field([row])
        try:
            target.set_focus()
        except Exception:
            pass
        try:
            if bool(target.iface_value.CurrentIsReadOnly):
                raise RuntimeError("Campo UIA está read-only.")
            target.iface_value.SetValue(str(text))
            actual = str(target.iface_value.CurrentValue)
            if actual != str(text):
                raise RuntimeError("O valor escrito não pôde ser relido exatamente.")
            return
        except Exception:
            try:
                rect = target.rectangle()
                click_physical(
                    *point_in_bounds([rect.left, rect.top, rect.right, rect.bottom])
                )
            except Exception:
                pass
            hwnd = int((self.window_metadata or {}).get("hwnd") or 0)
            paste_unicode(str(text), clear_first=True, hwnd=hwnd)

    def _search_wrapper(self):
        if self.search_key:
            ctrl = self.controls.get(self.search_key)
            if ctrl not in (None, "__keyboard_composer__"):
                return ctrl
        return None

    def _keyboard_open_from_search(self, contact):
        search = self._search_wrapper()
        if search is None:
            return False
        self._focus_whatsapp()
        focused = False
        try:
            search.set_focus()
            focused = bool(search.has_keyboard_focus())
        except Exception:
            focused = False
        if not focused:
            try:
                rect = search.rectangle()
                click_physical(*point_in_bounds([rect.left, rect.top, rect.right, rect.bottom], 0.5, 0.5))
                time.sleep(0.08)
            except Exception:
                pass
        # Down selects the first search result; Enter activates it.
        try:
            send_key_expression("down")
            time.sleep(0.10)
            send_key_expression("enter")
        except Exception:
            return False
        return self._wait_conversation_header(contact, 2.0)

    def _physical_open_target(self, target, contact, double=False):
        try:
            rect = target.rectangle()
            bounds = [rect.left, rect.top, rect.right, rect.bottom]
            # Prefer the left/center text area, away from timestamp/pin controls.
            point = point_in_bounds(bounds, 0.45, 0.50)
            self._focus_whatsapp()
            click_physical(*point, double=double)
            return self._wait_conversation_header(contact, 2.0)
        except Exception:
            return False

    def _raw_reacquire_contact(self, contact, timeout=5.0):
        deadline = time.monotonic() + max(0.5, float(timeout))
        last = None

        while time.monotonic() < deadline:
            win = self._attach()
            if _raw_header_present(win, contact):
                return None

            search, meta = _raw_find_search_control(win)
            if search is None or meta is None:
                last = "campo raw de busca ausente"
                time.sleep(0.12)
                continue

            try:
                if _raw_read_value(search) != contact:
                    _raw_set_value(search, contact)
                    time.sleep(0.20)
                    continue
            except Exception as exc:
                last = str(exc)
                time.sleep(0.12)
                continue

            rows = _raw_contact_rows(win, contact, meta["bounds"])
            if len(rows) == 1:
                return rows[0]["ctrl"]

            last = f"resultados lógicos encontrados: {len(rows)}"
            time.sleep(0.15)

        raise RuntimeError(
            "Não consegui readquirir o resultado raw do WhatsApp: "
            + str(last or "timeout")
        )

    def _find_verified_contact_point(self, target, contact):
        attempts = []
        for candidate in _contact_click_candidates(target, contact):
            point = tuple(candidate["point"])
            hit = uia_hit_test_chain(*point, max_ancestors=10)
            row = {
                "point": list(point),
                "source_bounds": candidate["bounds"],
                "hit_ok": bool(hit.get("ok")),
                "hit_chain": hit.get("chain", [])[:10],
                "matches_contact": _hit_chain_matches_contact(hit, contact),
            }
            attempts.append(row)
            if row["matches_contact"]:
                return point, attempts
        return None, attempts

    def _hit_tested_click_contact(self, target, contact, *, double=False):
        self._focus_whatsapp()
        point, attempts = self._find_verified_contact_point(target, contact)
        self.last_activation_trace.append({
            "phase": "hit_test",
            "double": bool(double),
            "candidates": attempts,
            "chosen_point": list(point) if point else None,
        })
        if point is None:
            return False

        click_physical(*point, double=double)
        verified = self._wait_conversation_header(contact, 2.5)
        self.last_activation_trace.append({
            "phase": "post_click_verify",
            "double": bool(double),
            "point": list(point),
            "verified": bool(verified),
            "evidence": dict(self.last_conversation_evidence or {}),
        })
        return verified

    def _keyboard_activate_raw_result(self, target, contact):
        """Use SelectionItem + Enter only when selection/focus evidence supports it."""
        try:
            target.iface_selection_item.Select()
        except Exception:
            return False

        selected = False
        try:
            selected = bool(target.iface_selection_item.CurrentIsSelected)
        except Exception:
            pass

        focused = False
        try:
            target.set_focus()
            focused = bool(target.has_keyboard_focus())
        except Exception:
            pass

        self.last_activation_trace.append({
            "phase": "selection_keyboard_probe",
            "selected": selected,
            "focused": focused,
        })

        # Selection evidence is required; focus is preferred but Chromium may
        # keep actual keyboard focus on the search edit while moving selection.
        if not selected:
            return False

        try:
            send_key_expression("enter")
        except Exception:
            return False

        verified = self._wait_conversation_header(contact, 2.5)
        self.last_activation_trace.append({
            "phase": "post_enter_verify",
            "verified": bool(verified),
            "evidence": dict(self.last_conversation_evidence or {}),
        })
        return verified

    def open_contact(self, key):
        self.last_activation_trace = []
        self.last_conversation_evidence = {}

        target = self._target(key)
        contact = self.contact_names.get(key, "")
        if not contact:
            raise RuntimeError("Contato associado ao resultado UIA foi perdido.")

        if self._conversation_header_present(contact):
            return

        # 1. Hit-test BEFORE the click. We only click when UIA says the chosen
        # screen point is actually inside this contact's result hierarchy.
        if self._hit_tested_click_contact(target, contact, double=False):
            return

        # Do not destroy useful evidence immediately. If the click changed the
        # right pane but header matching still failed, keep the structural dump
        # in last_activation_trace for the benchmark.
        first_evidence = dict(self.last_conversation_evidence or {})

        # 2. Reacquire fresh DOM and use UIA SelectionItem keyboard activation.
        try:
            target = self._raw_reacquire_contact(contact, timeout=3.0)
            if target is None and self._conversation_header_present(contact):
                return
            if target is not None and self._keyboard_activate_raw_result(target, contact):
                return
        except Exception as exc:
            self.last_activation_trace.append({
                "phase": "reacquire_for_keyboard_failed",
                "error": str(exc),
            })

        # 3. Fresh hit-tested double click.
        try:
            target = self._raw_reacquire_contact(contact, timeout=3.0)
            if target is None and self._conversation_header_present(contact):
                return
            if target is not None and self._hit_tested_click_contact(
                target, contact, double=True
            ):
                return
        except Exception as exc:
            self.last_activation_trace.append({
                "phase": "reacquire_for_double_failed",
                "error": str(exc),
            })

        self.last_activation_trace.append({
            "phase": "failure",
            "first_post_click_evidence": first_evidence,
            "final_evidence": dict(self.last_conversation_evidence or {}),
        })
        raise RuntimeError(
            "O contato raw foi localizado, mas nenhuma ativação verificada abriu "
            "a conversa. Consulte activation_trace: agora cada clique foi validado "
            "por UIA ElementFromPoint antes da injeção de mouse."
        )

    def send(self, contact, message):
        snap = self.observe(contact, message)
        if identity(snap.get("conversation")) != identity(contact):
            raise RuntimeError("A conversa correta não está aberta; envio bloqueado.")
        if snap.get("draft") != message:
            raise RuntimeError("O rascunho literal não corresponde à mensagem autorizada; envio bloqueado.")
        if not snap.get("complete"):
            raise RuntimeError("Árvore UIA incompleta antes do envio; operação interrompida.")

        composer = choose_text_field(snap["controls"], purpose="message")
        if composer.get("synthetic") or composer.get("automation_id") == "__jarvis_keyboard_composer__":
            # Explicit send path only: focus the verified composer and press Enter once.
            current = self._read_keyboard_composer(contact)
            if current != message:
                raise RuntimeError("O compositor mudou imediatamente antes do envio.")
            send_key_expression("enter")
            return

        rect = composer["bounds"]
        buttons = [
            c for c in snap["controls"]
            if c["control_type"] == "Button"
            and c["enabled"]
            and fold(c["name"]).strip() in ("enviar", "send", "enviar mensagem", "send message")
            and c["bounds"][0] >= rect[0]
            and abs(c["bounds"][1] - rect[1]) < 100
        ]
        if len(buttons) == 1:
            target = self._target(buttons[0]["key"])
            try:
                target.iface_invoke.Invoke()
            except Exception:
                target.click_input()
            return

        # No button exposed: Enter is acceptable only after exact draft re-read on
        # the already verified conversation, and is executed exactly once.
        try:
            target = self._target(composer["key"])
            target.set_focus()
        except Exception:
            pass
        send_key_expression("enter")

