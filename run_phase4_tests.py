"""Offline Phase 4 tests + project syntax compilation; no message is sent."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import py_compile
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def compile_project():
    count = 0
    excluded = {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        "data",
        "build",
        "dist",
    }
    with tempfile.TemporaryDirectory(prefix="phase4_compile_") as tmp:
        for directory, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in excluded]
            for filename in files:
                if filename.endswith(".py"):
                    source = Path(directory) / filename
                    destination = Path(tmp) / (
                        hashlib.sha256(str(source).encode()).hexdigest() + ".pyc"
                    )
                    py_compile.compile(
                        str(source), cfile=str(destination), doraise=True
                    )
                    count += 1
    print(f"Compilação/sintaxe: {count} arquivos Python OK.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Inspeção UIA somente leitura (Windows); não abre app nem envia.",
    )
    args = parser.parse_args()

    if args.probe:
        from runtime.phase4.whatsapp_uia import WhatsAppUIA

        adapter = WhatsAppUIA()
        diagnosis = adapter.diagnose()
        probe = adapter.probe_fields()
        control_probe = adapter.probe_controls()

        safe_candidates = []
        for row in diagnosis.get("candidates", []):
            safe_candidates.append(
                {
                    "hwnd": row.get("hwnd"),
                    "pid": row.get("pid"),
                    "ppid": row.get("ppid"),
                    "exe": row.get("exe"),
                    "title": row.get("title"),
                    "class_name": row.get("class_name"),
                    "visible": row.get("visible"),
                    "foreground": row.get("foreground"),
                    "alpha_zero": row.get("alpha_zero"),
                    "bounds": row.get("bounds"),
                    "uia_ok": row.get("uia_ok"),
                    "uia_descendants": row.get("uia_descendants"),
                    "uia_named": row.get("uia_named"),
                    "uia_fields": row.get("uia_fields"),
                    "uia_buttons": row.get("uia_buttons"),
                    "uia_whatsapp_hits": row.get("uia_whatsapp_hits"),
                    "accessibility_score": row.get("accessibility_score"),
                    "uia_error": row.get("uia_error"),
                }
            )

        print(
            json.dumps(
                {
                    "ok": probe.get("ok"),
                    "error": probe.get("error"),
                    "roots": diagnosis.get("roots", []),
                    "process_tree_size": len(diagnosis.get("tree_pids", [])),
                    "candidates": safe_candidates,
                    "chosen": diagnosis.get("chosen"),
                    "descendants": probe.get("descendants"),
                    "fields": probe.get("fields", []),
                    "structural_probe_ok": control_probe.get("ok"),
                    "structural_probe_error": control_probe.get("error"),
                    "controls": control_probe.get("controls", []),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0 if probe.get("ok") else 1

    compile_project()
    suite = unittest.defaultTestLoader.discover(
        str(ROOT / "tests"), pattern="test_phase4*.py"
    )
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
