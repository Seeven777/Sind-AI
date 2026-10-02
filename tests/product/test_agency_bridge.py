import asyncio
import json
from pathlib import Path

from jarvis.agents import AgencyAgentCatalog
from jarvis.app.product_runtime import start_product_runtime
from jarvis.missions import MissionPlanner
from jarvis.models import MockModelProvider
from jarvis.models.base import ModelResponse


def _write_fixture(root: Path):
    codex = root / "codex" / "agents"
    codex.mkdir(parents=True)
    repo = root / "agency-agents"
    (repo / "engineering").mkdir(parents=True)
    (repo / "marketing").mkdir(parents=True)
    (repo / "strategy").mkdir(parents=True)
    (repo / "engineering" / "engineering-backend-architect.md").write_text("# source", encoding="utf-8")
    (repo / "marketing" / "marketing-social-media-strategist.md").write_text("# source", encoding="utf-8")
    (repo / "divisions.json").write_text(json.dumps({
        "engineering": {"label": "Engineering"},
        "marketing": {"label": "Marketing"},
    }), encoding="utf-8")
    (codex / "engineering-backend-architect.toml").write_text(
        'name = "Backend Architect"\n'
        'description = "Designs backend APIs and database architecture."\n'
        'developer_instructions = "Produce robust backend architecture and API contracts."\n',
        encoding="utf-8",
    )
    (codex / "marketing-social-media-strategist.toml").write_text(
        'name = "Social Media Strategist"\n'
        'description = "Plans social media and Instagram campaigns."\n'
        'developer_instructions = "Create measurable cross-platform social strategy."\n',
        encoding="utf-8",
    )
    (repo / "strategy" / "runbooks.json").write_text(json.dumps({
        "runbooks": [{
            "slug": "marketing-campaign",
            "title": "Marketing Campaign",
            "roster": [{
                "group": "Core",
                "activation": "always",
                "agents": ["marketing-social-media-strategist"]
            }]
        }]
    }), encoding="utf-8")
    return codex, repo


def test_agency_catalog_loads_routes_and_runbooks(tmp_path: Path):
    codex, repo = _write_fixture(tmp_path)
    catalog = AgencyAgentCatalog(codex_agents_dir=codex, repo_root=repo)

    assert catalog.status()["agents"] == 2
    assert catalog.status()["runbooks"] == 1
    backend = catalog.get("engineering-backend-architect")
    assert backend.division == "engineering"
    assert backend.agent_id == "agency.engineering-backend-architect"
    assert "coding" in backend.capabilities

    routes = catalog.route("Implemente uma API backend em Python", limit=1)
    assert routes[0].slug == "engineering-backend-architect"
    assert routes[0].agent_id == "agency.engineering-backend-architect"

    assert catalog.runbook_agents("marketing-campaign") == (
        "agency.marketing-social-media-strategist",
    )


def test_mission_planner_inserts_external_specialist():
    class Router:
        def route(self, objective, limit=1):
            class Route:
                slug = "engineering-backend-architect"
                agent_id = "agency.engineering-backend-architect"
            return (Route(),)

    plan = MissionPlanner(specialist_router=Router(), specialist_limit=1).build(
        "Pesquise e implemente uma API backend em Python."
    )
    assert plan.agents == (
        "research.general",
        "intelligence.analyst",
        "agency.engineering-backend-architect",
        "engineering.developer",
        "review.verifier",
    )
    assert "agency specialists" in plan.reason


class TwoStepProvider(MockModelProvider):
    def __init__(self):
        super().__init__("unused")
        self.calls = 0

    def chat(self, messages, *, model=None, system=None):
        self.calls += 1
        if self.calls == 1:
            content = "# Estratégia\n\nPlano de campanha detalhado, mensurável e suficientemente completo para revisão."
        else:
            content = "# Revisão\n\nA entrega atende ao objetivo, preserva limites e está utilizável.\n\nVERDICT: PASS"
        return ModelResponse(content, model or "mock-model", "mock")


def test_product_runtime_registers_agency_agents_without_operator_tools(tmp_path: Path, monkeypatch):
    codex, repo = _write_fixture(tmp_path)
    monkeypatch.setenv("JARVIS_CODEX_AGENTS_DIR", str(codex))
    monkeypatch.setenv("JARVIS_AGENCY_AGENTS_ROOT", str(repo))

    async def run():
        provider = TwoStepProvider()
        rt = await start_product_runtime(tmp_path / "data", model_provider=provider)
        try:
            status = rt.agency_catalog.status()
            assert status["agents"] == 2
            card = rt.agent_registry.card("agency.marketing-social-media-strategist")
            assert card.tools == ()
            assert card.active is True
            assert rt.agent_router.status()["specialists"] == 2
            # HQ office remains the compact core, while Agent Directory exposes all.
            assert rt.hq.snapshot()["metrics"]["agents_total"] == 8
            assert any(a["id"] == card.agent_id for a in rt.hq.agent_directory())

            result = await rt.missions.run_with_agents(
                "Planeje uma campanha de Instagram.",
                agents=("agency.marketing-social-media-strategist",),
                title="Agency test",
                reason="test runbook",
            )
            assert result["agents"] == [
                "agency.marketing-social-media-strategist",
                "review.verifier",
            ]
            assert result["review_passed"] is True
            assert provider.calls == 2
        finally:
            await rt.close()

    asyncio.run(run())


def test_agency_catalog_scales_to_282_codex_definitions(tmp_path: Path):
    codex = tmp_path / "codex" / "agents"
    codex.mkdir(parents=True)
    for index in range(282):
        slug = f"engineering-specialist-{index:03d}"
        name = "Backend API Specialist" if index == 137 else f"Engineering Specialist {index:03d}"
        description = (
            "Designs backend API architecture in Python."
            if index == 137 else
            f"Engineering specialist number {index:03d} for software delivery."
        )
        (codex / f"{slug}.toml").write_text(
            f'name = "{name}"\n'
            f'description = "{description}"\n'
            f'developer_instructions = "Provide expert guidance for specialist {index:03d}."\n',
            encoding="utf-8",
        )

    catalog = AgencyAgentCatalog(codex_agents_dir=codex, repo_root=tmp_path / "missing-repo")
    assert catalog.status()["agents"] == 282
    assert len({d.agent_id for d in catalog.definitions()}) == 282
    routes = catalog.route("Implemente uma backend API em Python", limit=5)
    assert routes
    assert any(r.slug == "engineering-specialist-137" for r in routes)
