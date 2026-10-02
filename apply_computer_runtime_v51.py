from pathlib import Path

def main():
    root = Path(__file__).resolve().parent
    wa = root / "runtime" / "phase4" / "whatsapp_uia.py"
    bench = root / "computer_v51_benchmark.py"
    if not wa.exists() or not bench.exists():
        print("ERRO: arquivos V5.1 ausentes.")
        return 2

    text = wa.read_text(encoding="utf-8")
    markers = [
        "self.last_focus_trace = []",
        "self.shell_metadata = {}",
        "self._focus_whatsapp()",
    ]
    missing = [m for m in markers if m not in text]
    if missing:
        print("ERRO: marcadores V5.1 ausentes:", missing)
        return 2

    print("Computer Runtime V5.1 Foreground Hotfix instalado.")
    print("O benchmark não envia mensagens.")
    print(r'Teste: .\.venv\Scripts\python.exe .\run_computer_v51_tests.py')
    print(r'Benchmark: .\.venv\Scripts\python.exe .\computer_v51_benchmark.py --contact "Me (você)"')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
