from __future__ import annotations

import asyncio
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.autonomy.service import AutonomyService
from jarvis.models.mock import MockModelProvider


def test_self_evolution_path_guard_and_candidate_copy(tmp_path: Path):
    assert AutonomyService._safe_candidate_path("src/jarvis/brain/chat.py") == "src/jarvis/brain/chat.py"
    assert AutonomyService._safe_candidate_path("tests/product/test_x.py") == "tests/product/test_x.py"
    assert AutonomyService._safe_candidate_path("../secrets.txt") is None
    assert AutonomyService._safe_candidate_path("./src/jarvis/brain/chat.py") is None
    assert AutonomyService._safe_candidate_path("config/google_client.json") is None
    assert AutonomyService._safe_candidate_path("scripts/start.ps1") is None

    source = tmp_path / "source"
    target = tmp_path / "candidate"
    (source / "src/jarvis").mkdir(parents=True)
    (source / "src/jarvis/a.py").write_text("VALUE = 1\n", encoding="utf-8")
    (source / ".git").mkdir()
    (source / ".git/config").write_text("private", encoding="utf-8")
    AutonomyService._copy_project_for_candidate(source, target)
    assert (target / "src/jarvis/a.py").read_text(encoding="utf-8") == "VALUE = 1\n"
    assert not (target / ".git").exists()


def test_improvement_repository_accepts_promotion_lifecycle(tmp_path: Path):
    async def scenario():
        rt = await start_product_runtime(tmp_path, model_provider=MockModelProvider())
        try:
            proposal = rt.autonomy_repository.add_proposal(
                title="Teste de evolução",
                summary="validar estados",
                rationale="src/jarvis/brain/chat.py",
                risk="low",
            )
            pid = proposal["proposal_id"]
            rt.autonomy_repository.set_proposal_status(pid, "approved")
            rt.autonomy_repository.set_proposal_status(pid, "implementing")
            rt.autonomy_repository.set_proposal_status(pid, "prepared", {"tests_passed": True})
            rt.autonomy_repository.set_proposal_status(pid, "promoted")
            assert rt.autonomy_repository.get_proposal(pid)["status"] == "promoted"
            rt.autonomy_repository.set_proposal_status(pid, "rolled_back")
            assert rt.autonomy_repository.get_proposal(pid)["status"] == "rolled_back"
        finally:
            await rt.close()

    asyncio.run(scenario())
