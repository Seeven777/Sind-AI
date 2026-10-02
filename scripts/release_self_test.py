from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from datetime import datetime,timezone,timedelta
from pathlib import Path

from jarvis.app.product_runtime import start_product_runtime
from jarvis.models import ModelResponse


class ReleaseMockProvider:
    provider_id="mock"
    default_model="release-mock"

    def health(self):
        return {"status":"healthy","provider":"mock","models":[self.default_model]}

    def list_models(self):
        return [self.default_model]

    def chat(self,messages,*,model=None,system=None):
        system=system or ""
        if "planejador de ferramentas" in system.lower():
            content=json.dumps({
                "tool_id":"system.time","payload":{},"reason":"release self-test"
            })
        elif "skill builder" in system.lower():
            content=json.dumps({
                "executor_py":"def execute(payload):\n    return {'success': True, 'output': payload}",
                "test_py":"from executor import execute\n\ndef test_execute():\n    assert execute({'x': 1})['output']['x'] == 1",
                "capabilities":["release.skill"],
                "permissions":[],
            })
        elif "reviewer" in system.lower():
            content="Revisão concluída sem falhas materiais.\n\nVERDICT: PASS"
        else:
            content=(
                "Entrega de release suficientemente detalhada para validar o fluxo, "
                "o artifact persistente, o handoff e a continuidade do sistema."
            )
        return ModelResponse(content,model or self.default_model,self.provider_id)


async def boot_loop(base:Path,count:int=20):
    for _ in range(count):
        rt=await start_product_runtime(base,model_provider=ReleaseMockProvider())
        assert rt.foundation.health.snapshot()["status"]=="healthy"
        await rt.close()


async def scenario():
    base=Path(tempfile.mkdtemp(prefix="jarvis-v1-release-"))
    try:
        await boot_loop(base,20)

        inbox=base/"connectors"/"inbox"
        inbox.mkdir(parents=True,exist_ok=True)
        (inbox/"URGENTE-diretoria.txt").write_text(
            "URGENTE: revisar aprovação hoje.",encoding="utf-8"
        )

        rt=await start_product_runtime(base,model_provider=ReleaseMockProvider())
        try:
            await rt.connectors.sync_all()
            assert rt.connector_repository.counts()["unread"]>=1

            rt.memory.remember(
                "Interface principal deve permanecer simples.",
                memory_type="preference",importance=.9
            )
            assert rt.memory.context("Interface")

            project=rt.projects.create(
                "Release Project","Validar Jarvis v1",
                rt.workspace["workspace_id"]
            )
            assert project["status"]=="active"

            custom=rt.agent_factory.create(
                agent_id="custom.release",
                name="Release Specialist",
                mission="Validar entregas de release.",
                capabilities=["release"],
            )
            assert custom["agent_id"]=="custom.release"

            generic=await rt.orchestrator.handle(
                "Faça no computador uma consulta do relógio do sistema"
            )
            assert generic["metadata"]["status"]=="completed"

            write_request=await rt.orchestrator.handle(
                "Crie arquivo release/check.txt :: release-ok"
            )
            assert write_request["kind"]=="approval_required"
            approval_id=write_request["approval_id"]
            operator=rt.agent_registry.runtime("operations.operator")
            executed=await operator.resume_approval(approval_id)
            assert executed["status"]=="completed"
            assert Path(executed["output"]["path"]).read_text(encoding="utf-8")=="release-ok"

            mission=await rt.missions.run(
                "Pesquise, analise e crie uma campanha completa para teste de release.",
                title="Release mission"
            )
            assert mission["review_passed"] is True
            assert Path(mission["artifact_path"]).exists()

            skill=await rt.skill_generator.generate(
                "release.skill","Retornar o payload recebido"
            )
            assert skill["ready_for_install"] is True
            installed=rt.skill_manager.install(Path(skill["path"]))
            assert installed["skill_id"]=="release.skill"
            output=rt.skill_runner.execute("release.skill",{"ok":True})
            assert output["success"] is True

            run_at=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
            reminder=rt.scheduler_repository.create_once(
                "Release reminder","reminder",run_at,{"message":"release"}
            )
            scheduled=await rt.scheduler.run_due()
            assert any(x["job_id"]==reminder for x in scheduled)

            opportunity=rt.opportunities.scan()
            assert "items" in opportunity

            hq=rt.hq.snapshot()
            assert hq["core"]["name"]=="Jarvis"
            assert hq["metrics"]["agents_available"]>=8

            assert rt.capabilities.resolve("coding")["status"]=="available"
            assert rt.nodes.repository.list()

            print("PASS foundation")
            print("PASS 20 clean product boots")
            print("PASS connectors")
            print("PASS memory")
            print("PASS projects")
            print("PASS agent factory")
            print("PASS generic tool planning")
            print("PASS approval -> real write -> verification")
            print("PASS dynamic multi-agent mission")
            print("PASS skill generation -> tests -> install -> execute")
            print("PASS scheduler/reminder")
            print("PASS opportunity engine")
            print("PASS HQ")
            print("PASS capability resolver")
            print("PASS distributed node registry")
        finally:
            await rt.close()

        ui=Path(__file__).resolve().parents[1]/"src"/"jarvis"/"ui"/"hq_web"
        for name in (
            "companion.html","index.html","mission-control.html",
            "agents.html","projects.html","memory.html","system.html"
        ):
            assert (ui/name).is_file(),name
        print("PASS UI surfaces")
    finally:
        shutil.rmtree(base,ignore_errors=True)


if __name__=="__main__":
    asyncio.run(scenario())
