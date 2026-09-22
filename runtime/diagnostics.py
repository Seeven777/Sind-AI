import json
import threading
from datetime import datetime
from pathlib import Path


class RuntimeDiagnostics:
    def __init__(self, root_dir):
        self.root = Path(root_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.root / "runtime_events.jsonl"
        self.last_error_path = self.root / "last_error.json"
        self._lock = threading.Lock()

    def event(self, kind, **data):
        row = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "kind": str(kind),
            **data,
        }
        with self._lock:
            with self.events_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return row

    def error(self, where, error, **data):
        row = self.event("error", where=where, error=str(error), **data)
        try:
            self.last_error_path.write_text(
                json.dumps(row, indent=2, ensure_ascii=False, default=str),
                encoding="utf-8",
            )
        except Exception:
            pass
        return row

    def last_error(self):
        try:
            return json.loads(self.last_error_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def recent(self, limit=30):
        try:
            lines = self.events_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return []
        items = []
        for line in lines[-int(limit):]:
            try:
                items.append(json.loads(line))
            except Exception:
                continue
        return items
