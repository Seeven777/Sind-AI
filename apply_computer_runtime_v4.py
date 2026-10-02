from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    required = [
        root / "runtime" / "computer_v2.py",
        root / "runtime" / "phase4" / "whatsapp_uia.py",
        root / "computer_v4_benchmark.py",
    ]
    missing = [str(x.relative_to(root)) for x in required if not x.exists()]
    if missing:
        print("ERRO: arquivos V4 ausentes:", ", ".join(missing))
        return 2

    computer = (root / "runtime" / "computer_v2.py").read_text(encoding="utf-8")
    whatsapp = (root / "runtime" / "phase4" / "whatsapp_uia.py").read_text(encoding="utf-8")
    markers = [
        "_root_hwnd",
        "uia_hit_test_chain",
        "_find_verified_contact_point",
        "_raw_conversation_evidence",
    ]
    joined = computer + "\n" + whatsapp
    absent = [m for m in markers if m not in joined]
    if absent:
        print("ERRO: marcadores V4 ausentes:", absent)
        return 2

    print("Computer Runtime V4 Hit-Test instalado.")
    print("O benchmark não envia mensagens.")
    print(r'Teste: .\.venv\Scripts\python.exe .\run_computer_v4_tests.py')
    print(r'Benchmark: .\.venv\Scripts\python.exe .\computer_v4_benchmark.py --contact "Me (você)"')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
