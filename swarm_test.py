import tempfile
from pathlib import Path

from swarm.registry import AgentRegistry
from swarm.blackboard import SwarmBlackboard
from swarm.apprenticeship import ApprenticeshipEngine
from swarm.orchestrator import SwarmOrchestrator
from swarm.demonstration import DemonstrationTeacher




class FakeObserve:
    def __init__(self):
        self.active=False
        self.session_id=None
    def start(self,label="demo"):
        self.active=True; self.session_id="demo1"; return {"ok":True,"session_id":"demo1"}
    def stop(self):
        self.active=False; return {"ok":True,"session_id":self.session_id}
    def build_candidate(self,session_id,name=None):
        return {"ok":True,"candidate":{"name":name or "demo","steps":[{"tool":"open_app","args":{"app":"notepad"}}],"inputs":{}},"steps":1}
    def status(self):
        return {"ok":True,"active":self.active,"session_id":self.session_id}


class FakeSkills:
    def __init__(self): self.saved=None
    def save_parametric_skill(self, name, steps, inputs=None, description=""):
        self.saved={"name":name,"steps":steps,"inputs":inputs or {},"description":description}
        return {"ok":True,"name":name,"steps":len(steps)}

class FakeModels:
    def fast_model_name(self):
        return "fake-fast"
    def reason_model_name(self):
        return "fake-reason"
    def chat(self, messages, user_text="", tools=None, force=None):
        system = (messages[0].get("content") if messages else "").lower()
        if "compila ensinamentos" in system:
            content = "Abrir o sistema\nConsultar o cadastro\nValidar os dados\nSalvar somente após confirmação"
        elif "planner" in system:
            content = "1. Reunir contexto\n2. Executar etapas verificáveis\n3. Validar resultado"
        elif "researcher" in system:
            content = "Priorizar fonte oficial e registrar evidências antes de concluir."
        elif "institutional" in system:
            content = "Consultar CCT e base institucional antes de afirmar direitos."
        elif "content specialist" in system:
            content = "Estruturar gancho, consequência prática e CTA sem inventar fatos."
        elif "developer" in system:
            content = "Planejar alteração, teste e rollback."
        elif "reviewer" in system:
            content = "Resposta final revisada e pronta para o usuário."
        else:
            content = "Resposta executada pelos especialistas."
        return {"message": {"role": "assistant", "content": content}, "_jarvis_model": force or "fake"}


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    print("[OK]", name)


def main():
    registry = AgentRegistry()
    roles = registry.select("Pesquise dados e crie uma publicação para o SindPetshop", max_roles=3)
    ids = [x.id for x in roles]
    check("Registry selects specialists", "researcher" in ids and ("content" in ids or "institutional" in ids), ids)

    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        models = FakeModels()
        apprenticeship = ApprenticeshipEngine(td / "apprenticeship.db", models=models)

        r = apprenticeship.handle("Quero te ensinar como fazer uma homologação interna")
        check("Teaching starts", r.get("handled") and apprenticeship.active(), r)
        apprenticeship.handle("Primeiro abra o sistema interno e localize o cadastro do trabalhador.")
        apprenticeship.handle("Depois confira os documentos e valide os dados antes de salvar.")
        apprenticeship.handle("Nunca finalize sem a confirmação prevista no procedimento.")
        r = apprenticeship.handle("finalizar ensino")
        check("Teaching compiles", r.get("ok") and r.get("procedure_id"), r)

        rel = apprenticeship.relevant("faça uma homologação interna", limit=2)
        check("Learned procedure is retrieved", bool(rel), rel)
        check("Learned steps persisted", len(rel[0].get("steps", [])) >= 2, rel[0])

        board = SwarmBlackboard(td / "swarm.db")
        swarm = SwarmOrchestrator(
            models, registry, board, apprenticeship=apprenticeship,
            config={"swarm_enabled": True, "swarm_max_specialists": 2, "swarm_review_enabled": True},
        )

        check("Simple chat does not swarm", not swarm.should_swarm("olá, tudo bem?", []))
        check(
            "Complex objective swarms",
            swarm.should_swarm("Pesquise as fontes, analise os dados e planeje uma campanha completa para outubro", [1,2,3,4]),
        )

        bundle = swarm.prepare(
            "Planeje uma campanha completa do SindPetshop usando dados e fontes",
            base_context="Contexto institucional de teste.",
        )
        check("Swarm session created", bundle.get("session_id") and bundle.get("plan"), bundle)
        check("Blackboard receives entries", len(board.entries(bundle["session_id"])) >= 2)

        solved = swarm.solve(
            "Pesquise, analise e crie uma estratégia completa para uma campanha sindical",
            base_context="Contexto institucional.",
        )
        check("Reviewer finalizes", solved.get("answer") == "Resposta final revisada e pronta para o usuário.", solved)
        check("Swarm stats", board.stats().get("sessions", 0) >= 2, board.stats())

        # Procedure use feedback changes persistence instead of retraining the base model.
        proc_id = rel[0]["id"]
        apprenticeship.record_use([proc_id], success=True)
        refreshed = [x for x in apprenticeship.list()["items"] if x["id"] == proc_id][0]
        check("Procedure learns from successful use", refreshed["uses"] >= 1 and refreshed["successes"] >= 1, refreshed)

        # Teach by demonstration -> executable Skill.
        fake_observe=FakeObserve(); fake_skills=FakeSkills()
        demo=DemonstrationTeacher(fake_observe,fake_skills)
        started=demo.handle("Observe enquanto eu faço cadastrar um atendimento")
        check("Demonstration starts", started.get("ok") and fake_observe.active, started)
        finished=demo.handle("terminei a demonstração")
        check("Demonstration becomes skill", finished.get("ok") and fake_skills.saved and fake_skills.saved["name"]=="cadastrar um atendimento", finished)

    print("\nSwarm + Apprenticeship test concluído.")


if __name__ == "__main__":
    main()
