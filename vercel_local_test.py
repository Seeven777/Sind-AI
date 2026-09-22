import json
from pathlib import Path

BASE=Path(__file__).resolve().parent

def check(name, cond, detail=''):
    if not cond:
        raise AssertionError(f'{name}: {detail}')
    print('[OK]', name)

cfg=json.loads((BASE/'vercel.json').read_text(encoding='utf-8'))
check('No root app.py', not (BASE/'app.py').exists())
check('Desktop entrypoint renamed', (BASE/'jarvis_desktop.py').exists())
check('Vercel framework disabled', cfg.get('framework') is None, cfg)
check('Vercel static output', cfg.get('outputDirectory')=='vercel_dist', cfg)
check('Vercel build script', (BASE/'vercel_build.cjs').exists())
check('Portal index', (BASE/'vercel_portal'/'index.html').exists())
check('Installer present', (BASE/'vercel_portal'/'Install-Jarvis.ps1').exists())
check('Launcher protocol text', 'jarvis://open' in (BASE/'vercel_portal'/'app.js').read_text(encoding='utf-8'))
check('PowerShell registers protocol', 'Software\\Classes\\jarvis' in (BASE/'vercel_portal'/'Install-Jarvis.ps1').read_text(encoding='utf-8'))
print('\nVercel/local architecture test concluído.')
