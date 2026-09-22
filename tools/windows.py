import ctypes
import csv
import io
import subprocess
from ctypes import wintypes

def list_windows():
    user32 = ctypes.windll.user32
    items = []
    PROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def cb(hwnd, lparam):
        if user32.IsWindowVisible(hwnd):
            n = user32.GetWindowTextLengthW(hwnd)
            if n > 0:
                buf = ctypes.create_unicode_buffer(n + 1)
                user32.GetWindowTextW(hwnd, buf, n + 1)
                title = buf.value.strip()
                if title:
                    items.append(title)
        return True

    user32.EnumWindows(PROC(cb), 0)
    return {"ok": True, "windows": items[:100]}

def list_processes():
    p = subprocess.run(
        ["tasklist", "/FO", "CSV", "/NH"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
    )
    if p.returncode != 0:
        return {"ok": False, "error": p.stderr.strip() or "Falha ao listar processos."}
    rows = list(csv.reader(io.StringIO(p.stdout)))
    return {"ok": True, "processes": [{"name": r[0], "pid": r[1]} for r in rows if len(r) >= 2][:200]}
