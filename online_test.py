from pathlib import Path

from capabilities.hub import CapabilityHub
from website.inspector import WebsiteInspector
from web_search.engine import PublicWebSearch

BASE = Path(__file__).resolve().parent
HUB = CapabilityHub(
    BASE / "capabilities" / "catalog.json",
    Path.home() / "JarvisWorkspace" / "CapabilityCache",
    Path.home() / "JarvisData" / "capabilities" / "user_capabilities.json",
)

TESTS = [
    ("brasil.cep.v1", {"cep":"05010000"}),
    ("weather.geocode", {"name":"São Paulo","count":2}),
    ("crossref.works.search", {"query":"artificial intelligence","rows":1}),
    ("pypi.project", {"project":"requests"}),
    ("worldbank.data.population", {"country":"BR","date":"2024"}),
    ("github.repo.get", {"owner":"python","repo":"cpython"}),
    ("fx.rate.pair", {"base":"USD","quote":"BRL"}),
]

print("Teste online da Autonomy Expansion 0.7\n")
ok = 0

for cid, params in TESTS:
    r = HUB.execute(cid, params, timeout=20, force_refresh=True)
    mark = "OK" if r.get("ok") else "FALHOU"
    print(f"[{mark}] capability {cid}")
    if not r.get("ok"):
        print(" ", str(r.get("error",""))[:300])
    else:
        ok += 1

site = WebsiteInspector().check("seo_summary", "https://example.com")
print(f"[{'OK' if site.get('ok') else 'FALHOU'}] Website Inspector example.com")

search = PublicWebSearch().search("OpenAI", limit=3)
print(f"[{'OK' if search.get('ok') and search.get('count',0) > 0 else 'AVISO'}] Busca pública best-effort")
if not search.get("ok"):
    print(" ", search.get("error","")[:300])

print(f"\n{ok}/{len(TESTS)} integrações estruturadas responderam.")
print("A busca pública é best-effort e pode sofrer rate-limit; isso não invalida o Capability Hub.")
