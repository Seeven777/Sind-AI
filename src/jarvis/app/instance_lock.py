from __future__ import annotations

import ctypes
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from jarvis.core.errors import LockError


def _pid_exists(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


class InstanceLock:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.acquired = False

    def acquire(self, run_id: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "pid": os.getpid(),
            "run_id": run_id,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        for _ in range(2):
            try:
                fd = os.open(str(self.path), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(payload, f)
                self.acquired = True
                return
            except FileExistsError:
                try:
                    existing = json.loads(self.path.read_text(encoding="utf-8"))
                    pid = int(existing.get("pid", 0))
                except Exception:
                    pid = 0
                if pid and _pid_exists(pid):
                    raise LockError(f"Jarvis is already running with PID {pid}")
                try:
                    self.path.unlink()
                except OSError as exc:
                    raise LockError(f"Could not remove stale lock: {exc}") from exc
        raise LockError("Could not acquire Jarvis instance lock")

    def release(self) -> None:
        if self.acquired:
            try:
                self.path.unlink(missing_ok=True)
            finally:
                self.acquired = False
