"""Inicializa o backend OpenJarvis e a interface legada como uma aplicação."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


BASE = Path(__file__).resolve().parent
OPENJARVIS = BASE / ".venv-openjarvis" / "Scripts" / "jarvis.exe"
LEGACY_PYTHON = BASE / ".venv" / "Scripts" / "python.exe"
HEALTH_URL = "http://127.0.0.1:8000/health"


def backend_ready() -> bool:
    try:
        with urlopen(HEALTH_URL, timeout=1) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def require_file(path: Path, description: str) -> None:
    if not path.is_file():
        raise SystemExit(f"{description} não encontrado: {path}")


def main() -> int:
    require_file(OPENJARVIS, "Executável OpenJarvis")
    require_file(LEGACY_PYTHON, "Python do JARVIS")

    server = None
    if not backend_ready():
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        server = subprocess.Popen(
            [str(OPENJARVIS), "serve"],
            cwd=BASE,
            creationflags=flags,
        )
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            if server.poll() is not None:
                raise SystemExit(
                    f"O backend OpenJarvis encerrou com código {server.returncode}."
                )
            if backend_ready():
                break
            time.sleep(0.5)
        else:
            server.terminate()
            raise SystemExit("O backend OpenJarvis não ficou pronto em 45 segundos.")

    try:
        if "--check" in sys.argv[1:]:
            print("JARVIS integrado: backend OpenJarvis saudável.")
            return 0
        return subprocess.call([str(LEGACY_PYTHON), str(BASE / "app.py")], cwd=BASE)
    finally:
        if server is not None and server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=8)
            except subprocess.TimeoutExpired:
                server.kill()


if __name__ == "__main__":
    sys.exit(main())
