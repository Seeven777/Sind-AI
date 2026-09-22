import subprocess
from pathlib import Path


ALLOWED_APPS = {
    "notepad": ["notepad.exe"],
    "bloco de notas": ["notepad.exe"],
    "calc": ["calc.exe"],
    "calculadora": ["calc.exe"],
    "explorer": ["explorer.exe"],
    "explorador": ["explorer.exe"],
    "paint": ["mspaint.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe"],
}


def open_app(app):
    key = app.lower().strip()
    command = ALLOWED_APPS.get(key)

    if not command:
        return {"ok": False, "error": f"Aplicativo não permitido: {app}"}

    subprocess.Popen(command)
    return {"ok": True, "app": app}


def open_folder(path):
    p = Path(path).expanduser().resolve()
    if not p.exists() or not p.is_dir():
        return {"ok": False, "error": "Pasta não encontrada."}

    subprocess.Popen(["explorer.exe", str(p)])
    return {"ok": True, "path": str(p)}
