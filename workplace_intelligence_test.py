import json
import tempfile
from pathlib import Path

from workplace.engine import WorkplaceIntelligence
from workplace.commands import parse_workplace_command


BASE = Path(__file__).resolve().parent


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    print("[OK]", name)


class ServiceStub:
    def __init__(self):
        self.opened = []
    def open(self, service):
        self.opened.append(service)
        return {"ok": True, "service": service, "embedded": True}


class LongStub:
    def __init__(self):
        self.calls = []
    def create(self, goal, plan=None, **kwargs):
        self.calls.append({"goal": goal, "plan": plan, **kwargs})
        return {"ok": True, "data": {"id": 77, "goal": goal, "status": "queued"}}


def main():
    registry = json.loads((BASE / "workplace" / "playbooks.json").read_text(encoding="utf-8"))
    check("Exactly 144 new playbooks", len(registry["playbooks"]) == 144, len(registry["playbooks"]))
    check("12 workplace categories", len(registry["categories"]) == 12, registry["categories"])
    check("12 playbooks per category", all(x.get("count") == 12 for x in registry["categories"].values()), registry["categories"])
    check("All playbooks free-only", all(x.get("free_only") is True for x in registry["playbooks"]))
    check("Unique playbook IDs", len({x["id"] for x in registry["playbooks"]}) == 144)
    check("All playbooks have steps", all(len(x.get("steps", [])) >= 4 for x in registry["playbooks"]))
    check("All playbooks have agents", all(x.get("agents") for x in registry["playbooks"]))

    with tempfile.TemporaryDirectory() as raw:
        services = ServiceStub()
        long = LongStub()
        engine = WorkplaceIntelligence(
            BASE / "workplace" / "playbooks.json",
            Path(raw) / "workplace.db",
            services=services,
            long_horizon=long,
            config={"workplace_auto_context": True, "workplace_max_context_playbooks": 3},
        )
        stats = engine.stats()
        check("Stats expose 144 playbooks", stats["playbooks"] == 144, stats)
        check("Search finds dashboard analytics", engine.search("resumo semanal do dashboard")["items"][0]["category"] == "analytics")
        check("Search finds CCT", any(x["category"] == "cct" for x in engine.search("comparar duas CCTs", limit=5)["items"]))
        check("Search finds onboarding", any(x["category"] == "team" for x in engine.search("onboarding novo funcionário", limit=5)["items"]))
        context = engine.context("campanha de data-base e instagram")
        check("Automatic playbook context", context["ok"] and bool(context["text"]), context)

        target = "workplace.analytics.weekly_summary"
        started = engine.start_long_horizon(target, request="Analise a semana")
        check("Playbook starts Long-Horizon job", started["ok"] and started["data"]["id"] == 77, started)
        check("Institutional services are pre-opened", "insights_dashboard" in services.opened, services.opened)
        check("Playbook plan reaches Long-Horizon", len(long.calls[-1]["plan"]) >= 4, long.calls[-1])
        check("Usage persisted", engine.stats()["usage"].get("started", 0) == 1, engine.stats())
        engine.record_outcome(playbook_id=target, status="completed", note="feito")
        check("Outcome learning persisted", engine.stats()["usage"].get("completed", 0) == 1, engine.stats())

    check("Natural list command", parse_workplace_command("Liste playbooks")["action"] == "list")
    check("Natural search command", parse_workplace_command("Qual playbook para analisar Instagram?")["action"] == "search")
    check("Natural run command", parse_workplace_command("Use o playbook resumo semanal de performance")["action"] == "run")

    agent = (BASE / "core" / "agent.py").read_text(encoding="utf-8")
    check("Agent tool: search playbooks", '"name":"search_workplace_playbooks"' in agent)
    check("Agent tool: run playbook", '"name":"run_workplace_playbook"' in agent)
    check("System prompt injects workplace context", "PLAYBOOKS DE TRABALHO RELEVANTES" in agent)

    habitat = (BASE / "ui" / "habitat.py").read_text(encoding="utf-8")
    ui = (BASE / "ui" / "web" / "index.html").read_text(encoding="utf-8")
    js = (BASE / "ui" / "web" / "app.js").read_text(encoding="utf-8")
    check("Desktop bridge searches playbooks", "def searchPlaybooks" in habitat)
    check("Desktop bridge starts playbooks", "def startPlaybook" in habitat)
    check("Control Center playbook search", 'id="playbookQuery"' in ui)
    check("Context playbook suggestions", 'id="workplaceSuggestionList"' in ui)
    check("One-click playbook start", "function startPlaybook" in js)

    print("\nWorkplace Intelligence test concluído.")


if __name__ == "__main__":
    main()
