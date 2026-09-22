from pathlib import Path
import json

from actions.commands import parse_action_command
from actions.hub import ActionHub
from workflows.commands import parse_workflow_command
from workflows.hub import WorkflowHub

BASE = Path(__file__).resolve().parent

def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    print("[OK]", name)

wf_cases = {
    "Procure workflows para monitorar um site.": ("search", "monitorar um site"),
    "Mostre os workflows relacionados ao assistente da equipe.": ("search", "assistente da equipe"),
    "Mostre os workflows.": ("stats", None),
}
for prompt, expected in wf_cases.items():
    parsed = parse_workflow_command(prompt)
    check(f"workflow parser: {prompt}", parsed and parsed["action"] == expected[0], parsed)
    if expected[1]:
        check("workflow query", parsed["query"] == expected[1], parsed)

action_cases = {
    "Procure ações para criar uma automação diária.": ("search", "criar uma automação diária"),
    "Mostre as ações relacionadas à fila de aprovações.": ("search", "fila de aprovações"),
    "Mostre as ações disponíveis para administrar usuários e permissões do assistente da equipe.": (
        "search", "administrar usuários e permissões do assistente da equipe"
    ),
    "Mostre as ações.": ("stats", None),
}
for prompt, expected in action_cases.items():
    parsed = parse_action_command(prompt)
    check(f"action parser: {prompt}", parsed and parsed["action"] == expected[0], parsed)
    if expected[1]:
        check("action query", parsed["query"] == expected[1], parsed)

ah = ActionHub(BASE / "actions" / "catalog.json", {})
wh = WorkflowHub(BASE / "workflows" / "catalog.json", ah)

r = wh.search("monitorar um site", 10)
check("workflow monitor result", any(x["id"].startswith("workflow.monitor.") for x in r["items"]), r["items"][:5])

r = wh.search("assistente da equipe", 10)
check("workflow team assistant result", any("team" in x["id"] or "portal" in x["id"] for x in r["items"]), r["items"][:5])

r = ah.search("administrar usuários e permissões do assistente da equipe", 12)
check("team actions prioritized", any(x["id"].startswith("team.") for x in r["items"][:6]), r["items"][:8])

r = ah.search("fila de aprovações", 10)
check("approval actions prioritized", any(x["id"].startswith("approval.") for x in r["items"][:5]), r["items"][:5])

print("\nCatalog routing/search test concluído.")
