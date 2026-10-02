from __future__ import annotations

import sqlite3
from pathlib import Path

from jarvis.core.errors import StorageError


class Database:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.connection: sqlite3.Connection | None = None

    def open(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            conn = sqlite3.connect(self.path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA foreign_keys=ON;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            conn.execute("PRAGMA busy_timeout=5000;")
            self.connection = conn
            return conn
        except sqlite3.Error as exc:
            raise StorageError(f"Could not open database {self.path}: {exc}") from exc

    def conn(self) -> sqlite3.Connection:
        if self.connection is None:
            return self.open()
        return self.connection

    def close(self) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def health(self) -> bool:
        try:
            row = self.conn().execute("SELECT 1 AS ok").fetchone()
            return bool(row and row["ok"] == 1)
        except sqlite3.Error:
            return False
