import tkinter as tk

def get_clipboard_text():
    root = tk.Tk()
    root.withdraw()
    try:
        text = root.clipboard_get()
        return {"ok": True, "text": text}
    except Exception:
        return {"ok": True, "text": ""}
    finally:
        root.destroy()

def set_clipboard_text(text):
    root = tk.Tk()
    root.withdraw()
    try:
        root.clipboard_clear()
        root.clipboard_append(str(text))
        root.update()
        return {"ok": True}
    finally:
        root.destroy()
