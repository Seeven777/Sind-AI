"""Safe cleanup/report utility for the Sind-AI working tree.

Default mode is report-only. It never touches JarvisData, SQLite databases,
user secrets, source files, Git metadata or Python virtual environments.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


CACHE_DIR_NAMES = {
    "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".cache"
}
REBUILDABLE_DIRS = {
    "dist", "build", "htmlcov"
}
NEVER_TOUCH = {
    ".git", ".venv", ".venv-openjarvis", "venv", "env", "JarvisData"
}


def size_of(path: Path) -> int:
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if d not in NEVER_TOUCH]
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except OSError:
                pass
    return total


def fmt(n: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(n)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{n} B"


def tracked_paths(root: Path) -> set[str]:
    try:
        proc = subprocess.run(
            ["git", "ls-files"], cwd=root, check=True, capture_output=True, text=True
        )
        return {line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()}
    except Exception:
        return set()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="remove only safe cache artifacts")
    parser.add_argument(
        "--rebuildable", action="store_true",
        help="also include untracked dist/build/htmlcov directories"
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    tracked = tracked_paths(root)
    candidates: list[tuple[Path, str]] = []

    for path in root.rglob("*"):
        try:
            rel = path.relative_to(root)
        except ValueError:
            continue
        parts = rel.parts
        if any(part in NEVER_TOUCH for part in parts):
            continue
        rel_posix = rel.as_posix()
        if rel_posix in tracked:
            continue
        if path.is_dir() and path.name in CACHE_DIR_NAMES:
            candidates.append((path, "cache"))
        elif args.rebuildable and path.is_dir() and path.name in REBUILDABLE_DIRS:
            candidates.append((path, "rebuildable"))
        elif path.is_file() and (path.suffix in {".pyc", ".pyo"} or path.name.endswith(".log")):
            candidates.append((path, "generated"))

    # Remove nested duplicates from reporting/removal.
    unique: list[tuple[Path, str]] = []
    for path, kind in sorted(candidates, key=lambda x: len(x[0].parts)):
        if any(parent in path.parents for parent, _ in unique):
            continue
        unique.append((path, kind))

    total = sum(size_of(path) for path, _ in unique)
    print(f"Candidatos seguros: {len(unique)} | espaço estimado: {fmt(total)}")
    for path, kind in unique[:200]:
        print(f"[{kind:11}] {path.relative_to(root)} ({fmt(size_of(path))})")
    if len(unique) > 200:
        print(f"... mais {len(unique) - 200} item(ns)")

    suspicious_tracked = [
        p for p in sorted(tracked)
        if "/__pycache__/" in f"/{p}" or p.endswith((".pyc", ".pyo"))
    ]
    if suspicious_tracked:
        print("\nArtefatos gerados que estão RASTREADOS no Git (não removidos automaticamente):")
        for item in suspicious_tracked[:80]:
            print("  -", item)

    if not args.apply:
        print("\nModo relatório. Para remover somente os candidatos acima: --apply")
        return 0

    removed = 0
    for path, _ in unique:
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
            removed += 1
        except OSError as exc:
            print(f"Falha ao remover {path}: {exc}")
    print(f"\nRemovidos: {removed}. JarvisData e ambientes virtuais foram preservados.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
