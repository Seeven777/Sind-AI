from __future__ import annotations

import re
import sqlite3
from pathlib import Path

from jarvis.core.errors import MigrationError

_PATTERN = re.compile(r"^(?P<version>\d{4})_(?P<name>.+)\.sql$")


class MigrationEngine:
    def __init__(self, connection: sqlite3.Connection, migrations_dir: Path) -> None:
        self.connection = connection
        self.migrations_dir = Path(migrations_dir)

    def _ensure_table(self) -> None:
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def applied_versions(self) -> set[int]:
        self._ensure_table()
        rows = self.connection.execute("SELECT version FROM schema_migrations").fetchall()
        return {int(row["version"]) for row in rows}

    def discover(self) -> list[tuple[int, str, Path]]:
        items: list[tuple[int, str, Path]] = []
        if not self.migrations_dir.exists():
            return items
        for path in self.migrations_dir.iterdir():
            match = _PATTERN.match(path.name)
            if match:
                items.append((int(match.group("version")), match.group("name"), path))
        items.sort(key=lambda x: x[0])
        return items

    def apply_pending(self) -> list[int]:
        applied = self.applied_versions()
        completed: list[int] = []
        for version, name, path in self.discover():
            if version in applied:
                continue
            sql = path.read_text(encoding="utf-8")
            try:
                self.connection.execute("BEGIN IMMEDIATE")
                self.connection.executescript(sql)
                self.connection.execute(
                    "INSERT INTO schema_migrations(version,name,applied_at) "
                    "VALUES(?,?,strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
                    (version, name),
                )
                self.connection.commit()
                completed.append(version)
            except (sqlite3.Error, OSError) as exc:
                self.connection.rollback()
                raise MigrationError(f"Migration {path.name} failed: {exc}") from exc
        return completed
