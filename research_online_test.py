from pathlib import Path

from web_search.engine import PublicWebSearch
from research.engine import ResearchEngine


print('=== Jarvis Research Engine 0.7.3 — teste online ===\n')
engine = ResearchEngine(PublicWebSearch(user_agent='JarvisSindPet/0.7.3-test'))

query = 'NR-1'
print('[1] Pesquisa + normalização de URLs...')
r = engine.search(query, limit=8, official_first=True)
print('OK:', r.get('ok'), '| fontes:', r.get('count'))
for item in r.get('items', [])[:8]:
    print(f" - {item.get('authority_score'):>3} | {item.get('source_type'):<18} | {item.get('url')}")

if not r.get('ok'):
    print('\nFALHA:', r.get('attempts'))
    raise SystemExit(1)

if any('bing.com/ck/' in (x.get('url') or '') for x in r.get('items', [])):
    raise SystemExit('FALHA: redirect do Bing ainda apareceu como URL final.')

print('\n[2] Coletando evidências de até 5 fontes...')
bundle = engine.evidence_pack(query, limit=5, official_first=True)
print('OK:', bundle.get('ok'), '| cards:', bundle.get('count'))
for c in bundle.get('cards', []):
    print(f" - {c.get('authority_score'):>3} | {'OFICIAL' if c.get('official') else c.get('source_type')} | {c.get('domain')} | {len(c.get('sentences', []))} evidência(s)")

if not bundle.get('ok'):
    raise SystemExit('FALHA: não foi possível montar evidence pack.')

print('\n[3] Síntese determinística (não usa Ollama)...')
print(engine.deterministic_summary(bundle)[:4000])
print('\n[OK] Research Engine respondeu sem depender do modelo local.')
