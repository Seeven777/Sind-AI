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
    excluded = {'.git', '.venv', 'venv', 'node_modules', '__pycache__', 'data', 'build', 'dist'}
    with tempfile.TemporaryDirectory(prefix='phase4_compile_') as tmp:
        for directory, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in excluded]
            for filename in files:
                if filename.endswith('.py'):
                    source = Path(directory) / filename
                    destination = Path(tmp) / (hashlib.sha256(str(source).encode()).hexdigest() + '.pyc')
                    py_compile.compile(str(source), cfile=str(destination), doraise=True)
                    count += 1
    print(f'Compilação/sintaxe: {count} arquivos Python OK.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true', help='Inspeção UIA somente leitura (Windows); não abre app nem envia.')
    args = parser.parse_args()
    if args.probe:
        from runtime.phase4.whatsapp_uia import WhatsAppUIA
        result = WhatsAppUIA().observe('', '')
        # Field labels/IDs only; no conversation history, contact list or draft values.
        print(json.dumps({'ok': result.get('ok'), 'complete': result.get('complete'), 'error': result.get('error'),
                          'fields': [r for r in result.get('controls', []) if r.get('control_type') in ('Edit', 'Document')]}, ensure_ascii=False, indent=2))
        return 0 if result.get('ok') else 1
    compile_project()
    suite = unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern='test_phase4_real_execution.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
