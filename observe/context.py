import ctypes
import os
import sys
from pathlib import Path

from observe.app_registry import identify_app, infer_document_hint


PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _process_image_name(pid):
    if not pid or sys.platform != "win32":
        return ""
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
    if not handle:
        return ""
    try:
        size = ctypes.c_ulong(32768)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
    except Exception:
        return ""
    finally:
        kernel32.CloseHandle(handle)
    return ""


def foreground_snapshot():
    """Return a cheap foreground-window snapshot using only the Python stdlib/WinAPI."""
    if sys.platform != "win32":
        return {
            "ok": True,
            "platform": sys.platform,
            "handle": None,
            "pid": os.getpid(),
            "process_name": Path(sys.executable).name,
            "process_path": "",
            "window_title": "",
            "app_id": "unknown",
            "app_label": "Aplicativo desconhecido",
            "document_hint": "",
        }

    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        title_len = user32.GetWindowTextLengthW(hwnd)
        title_buf = ctypes.create_unicode_buffer(title_len + 1)
        user32.GetWindowTextW(hwnd, title_buf, title_len + 1)

        pid = ctypes.c_ulong(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_path = _process_image_name(pid.value)
        process_name = Path(process_path).name if process_path else ""
        app = identify_app(process_name, title_buf.value)
        hint = infer_document_hint(app["id"], title_buf.value)
        return {
            "ok": True,
            "platform": sys.platform,
            "handle": int(hwnd) if hwnd else None,
            "pid": int(pid.value or 0),
            "process_name": process_name,
            "process_path": process_path,
            "window_title": title_buf.value.strip(),
            "app_id": app["id"],
            "app_label": app["label"],
            "document_hint": hint,
        }
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "platform": sys.platform,
            "handle": None,
            "pid": 0,
            "process_name": "",
            "process_path": "",
            "window_title": "",
            "app_id": "unknown",
            "app_label": "Aplicativo desconhecido",
            "document_hint": "",
        }
