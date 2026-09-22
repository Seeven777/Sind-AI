import json
from pathlib import Path

from runtime.intent_router import parse_fast_intent
from web_search.engine import PublicWebSearch

BASE = Path(__file__).resolve().parent


def check(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    print(f"[OK] {name}")


# 1) The failed user sentence must now be routed without generic Agent Runtime.
intent = parse_fast_intent(
    "Pesquise na web sobre NR-1, encontre fontes relevantes e crie um arquivo no workspace com um resumo."
)
check(
    "Research-to-file intent",
    intent and intent.get("kind") == "research_to_file" and intent.get("query") == "NR-1",
    intent,
)

# 2) Search fallback must continue after an empty provider.
engine = PublicWebSearch()
engine._ddg_html = lambda q, limit: []
engine._ddg_lite = lambda q, limit: []
engine._bing = lambda q, limit: [
    {"title": "NR-1 oficial", "url": "https://example.com/nr1", "snippet": "resultado de teste"}
]
engine._google_html = lambda q, limit: []
result = engine.search("NR-1", 8)
check("Multi-provider web fallback", result.get("ok") and result.get("provider") == "Bing HTML", result)

# 3) The technical dashboard was replaced by one conversational workspace.
html = (BASE / "ui" / "web" / "index.html").read_text(encoding="utf-8")
for element in ("conversation", "conversationList", "inspector", "controlOverlay", "sourceSearchResults"):
    check(f"Clean UI element {element}", f'id="{element}"' in html)
for obsolete in ("view-actions", "view-workflows", "view-automations", "view-monitors", "view-connectors"):
    check(f"Old permanent view removed: {obsolete}", f'id="{obsolete}"' not in html)

# 4) Compact bridge keeps advanced infrastructure callable without permanent tabs.
habitat = (BASE / "ui" / "habitat.py").read_text(encoding="utf-8")
for method in ("openConversation", "searchPublicSources", "searchActions", "searchWorkflows"):
    check(f"Bridge {method}", f"def {method}" in habitat)

# 5) Foundation release adds >100 actual composite workflows.
workflows = json.loads((BASE / "workflows" / "catalog.json").read_text(encoding="utf-8"))["workflows"]
foundation = [w for w in workflows if w.get("id", "").startswith("workflow.foundation.")]
check("Foundation workflows >= 100", len(foundation) >= 100, len(foundation))

print("\nFoundation regression test concluído.")
