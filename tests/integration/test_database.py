from pathlib import Path
from jarvis.storage import Database, MigrationEngine


def test_database_wal_and_reopen(tmp_path: Path):
    path = tmp_path / "jarvis.db"
    db = Database(path)
    conn = db.open()
    MigrationEngine(conn, Path(__file__).resolve().parents[2] / "migrations").apply_pending()
    mode = conn.execute("PRAGMA journal_mode").fetchone()[0].lower()
    assert mode == "wal"
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    db.close()

    db2 = Database(path)
    conn2 = db2.open()
    versions = conn2.execute("SELECT version FROM schema_migrations").fetchall()
    assert [row[0] for row in versions] == [1, 2, 3, 4, 5]
    db2.close()
