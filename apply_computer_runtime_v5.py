from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    required = [
        root / "runtime" / "computer_v2.py",
        root / "runtime" / "phase4" / "whatsapp_uia.py",
        root / "computer_v5_benchmark.py",
    ]
    missing = [str(x.relative_to(root)) for x in required if not x.exists()]
    if missing:
        print("ERRO: arquivos V5 ausentes:", ", ".join(missing))
        return 2

    joined = "\n".join(
        p.read_text(encoding="utf-8")
        for p in required[:2]
    )
    markers = [
        "choose_whatsapp_shell",
        "foreground_window_info",
        "last_focus_trace",
        "HWND_TOPMOST",
    ]
    absent = [m for m in markers if m not in joined]
    if absent:
        print("ERRO: marcadores V5 ausentes:", absent)
        return 2

    print("Computer Runtime V5 Foreground Ownership instalado.")
    print("O benchmark não envia mensagens.")
    print(r'Teste: .\.venv\Scripts\python.exe .\run_computer_v5_tests.py')
    print(r'Benchmark: .\.venv\Scripts\python.exe .\computer_v5_benchmark.py --contact "Me (você)"')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
