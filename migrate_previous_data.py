import json
import shutil
import sqlite3
import sys
from pathlib import Path

HOME = Path.home()
VAULT = HOME / "JarvisData"


def ensure_schema(dest_db):
    dest_db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(dest_db) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL DEFAULT 'fact',
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_memories_key ON memories(key);
            CREATE TABLE IF NOT EXISTS aliases (
                alias TEXT PRIMARY KEY COLLATE NOCASE,
                target TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)


def migrate_memory(old_db, dest_db):
    if not old_db.exists():
        return 0, 0
    ensure_schema(dest_db)
    memories = aliases = 0
    with sqlite3.connect(old_db) as src, sqlite3.connect(dest_db) as dst:
        src.row_factory = sqlite3.Row
        try:
            rows = src.execute("SELECT kind,key,value,created_at,updated_at FROM memories").fetchall()
            for r in rows:
                existing = dst.execute("SELECT id FROM memories WHERE lower(key)=lower(?)", (r['key'],)).fetchone()
                if existing:
                    dst.execute("UPDATE memories SET kind=?,value=?,updated_at=? WHERE id=?", (r['kind'],r['value'],r['updated_at'],existing[0]))
                else:
                    dst.execute("INSERT INTO memories(kind,key,value,created_at,updated_at) VALUES(?,?,?,?,?)", tuple(r))
                memories += 1
        except sqlite3.Error:
            pass
        try:
            rows = src.execute("SELECT alias,target,created_at,updated_at FROM aliases").fetchall()
            for r in rows:
                dst.execute("""
                    INSERT INTO aliases(alias,target,created_at,updated_at) VALUES(?,?,?,?)
                    ON CONFLICT(alias) DO UPDATE SET target=excluded.target,updated_at=excluded.updated_at
                """, tuple(r))
                aliases += 1
        except sqlite3.Error:
            pass
    return memories, aliases


def migrate_skills(old_root, dest_root):
    old_lib = old_root / "skills" / "library"
    dest_lib = dest_root / "skills" / "library"
    dest_lib.mkdir(parents=True, exist_ok=True)
    count = 0
    if old_lib.exists():
        for f in old_lib.glob("*.json"):
            shutil.copy2(f, dest_lib / f.name)
            count += 1
    old_log = old_root / "skills" / "action_history.jsonl"
    dest_log = dest_root / "skills" / "action_history.jsonl"
    if old_log.exists():
        dest_log.parent.mkdir(parents=True, exist_ok=True)
        old_lines = old_log.read_text(encoding="utf-8", errors="replace").splitlines()
        existing = set(dest_log.read_text(encoding="utf-8", errors="replace").splitlines()) if dest_log.exists() else set()
        with dest_log.open("a", encoding="utf-8") as out:
            for line in old_lines:
                if line and line not in existing:
                    out.write(line + "\n")
    return count


def migrate_user_capabilities(old_root, dest_root):
    old = old_root / "data" / "user_capabilities.json"
    if not old.exists():
        return 0
    dest = dest_root / "capabilities" / "user_capabilities.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        old_items = json.loads(old.read_text(encoding="utf-8"))
    except Exception:
        return 0
    current = []
    if dest.exists():
        try:
            current = json.loads(dest.read_text(encoding="utf-8"))
        except Exception:
            current = []
    by_id = {x.get('id'): x for x in current if isinstance(x,dict) and x.get('id')}
    for x in old_items:
        if isinstance(x,dict) and x.get('id'):
            by_id[x['id']] = x
    dest.write_text(json.dumps(sorted(by_id.values(), key=lambda x:x['id']),ensure_ascii=False,indent=2),encoding='utf-8')
    return len(old_items)


def main():
    if len(sys.argv) > 1:
        old_root = Path(sys.argv[1].strip('"')).resolve()
    else:
        raw = input("Cole o caminho da pasta da versao anterior do Jarvis: ").strip().strip('"')
        old_root = Path(raw).resolve()
    if not old_root.exists():
        print("Pasta anterior nao encontrada:", old_root)
        return 1

    VAULT.mkdir(parents=True, exist_ok=True)
    mem, aliases = migrate_memory(old_root / "data" / "jarvis_memory.db", VAULT / "memory" / "jarvis_memory.db")
    skills = migrate_skills(old_root, VAULT)
    caps = migrate_user_capabilities(old_root, VAULT)
    print("Migracao concluida.")
    print(f"Memorias: {mem}")
    print(f"Aliases: {aliases}")
    print(f"Skills: {skills}")
    print(f"Capacidades aprendidas: {caps}")
    print("Data Vault:", VAULT)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
