"""Idempotent installer/checker for Computer Runtime V3 Raw Bridge."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent

    # V3 is layered on the V2 routing/controller foundation. If the V2 early
    # route is absent, apply the bundled V2 wiring once.
    agent = root / "core" / "agent.py"
    text = agent.read_text(encoding="utf-8")
    if "# COMPUTER_RUNTIME_V2_EARLY_WHATSAPP" not in text:
        spec = importlib.util.spec_from_file_location(
            "apply_computer_runtime_v2",
            root / "apply_computer_runtime_v2.py",
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        code = int(mod.main() or 0)
        if code:
            return code

    required = [
        root / "runtime" / "computer_v2.py",
        root / "runtime" / "phase4" / "whatsapp_uia.py",
        root / "computer_v3_benchmark.py",
    ]
    missing = [str(x.relative_to(root)) for x in required if not x.exists()]
    if missing:
        print("ERRO: arquivos V3 ausentes:", ", ".join(missing))
        return 2

    source = (root / "runtime" / "phase4" / "whatsapp_uia.py").read_text(encoding="utf-8")
    markers = (
        "_raw_find_search_control",
        "_raw_contact_rows",
        "_raw_reacquire_contact",
        '"raw_bridge": True',
    )
    absent = [x for x in markers if x not in source]
    if absent:
        print("ERRO: whatsapp_uia.py não contém todos os marcadores V3:", absent)
        return 2

    print("Computer Runtime V3 Raw Bridge instalado.")
    print("Nenhuma mensagem é enviada pelos benchmarks.")
    print(r"Teste: .\.venv\Scripts\python.exe .\run_computer_v3_tests.py")
    print(r"Benchmark: .\.venv\Scripts\python.exe .\computer_v3_benchmark.py --contact ""Me (você)""")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
