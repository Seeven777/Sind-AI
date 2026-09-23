import json
import tempfile
from pathlib import Path

from acquisition.engine import CapabilityAcquisitionEngine
from acquisition.commands import parse_acquisition_command
from skills.store import SkillStore


class FakeModels:
    def chat(self, messages, user_text="", force=None, **kwargs):
        payload = {
            "name": "Automatizar relatório",
            "description": "Skill composta automaticamente a partir de primitivas existentes.",
            "inputs": {},
            "steps": [
                {"kind": "action", "id": "browser.click", "params": {}},
                {"kind": "action", "id": "browser.type", "params": {}},
            ],
        }
        return {"message": {"content": json.dumps(payload, ensure_ascii=False)}}


class FakeActions:
    def __init__(self):
        self.items = {
            "browser.click": {
                "id": "browser.click", "description": "Clique em um controle", "risk": "act",
                "params": {"name": {"required": True}},
            },
            "browser.type": {
                "id": "browser.type", "description": "Digita texto em um controle", "risk": "act",
                "params": {"text": {"required": True}},
            },
        }
    def search(self, query, limit=6):
        # Keep primitives available but deliberately low semantic similarity.
        return {"ok": True, "items": list(self.items.values())[:limit], "count": len(self.items)}
    def get(self, action_id):
        return self.items.get(action_id)


class EmptyWorkflows:
    def search(self, query, limit=6): return {"ok": True, "items": [], "count": 0}
    def get(self, workflow_id): return None


class FakeCapabilities:
    def __init__(self): self.items = {}
    def search(self, query, limit=6): return {"ok": True, "items": [], "count": 0}
    def get(self, capability_id): return self.items.get(capability_id)
    def discover_public_apis(self, query, limit=5): return {"ok": True, "items": [], "count": 0}
    def import_openapi(self, spec_url, prefix="acquired", max_operations=40):
        return {"ok": True, "imported": 2, "title": "Test API"}


class FakeApprenticeship:
    def relevant(self, query, limit=6): return []


class FakePublicData:
    def recommend(self, query, limit=6): return {"ok": True, "items": []}
    def discover_interfaces(self, url, save=True):
        return {"ok": True, "interfaces": [{"kind": "openapi", "url": "https://example.com/openapi.json"}]}


class FakeServices:
    def context(self, query, limit=6): return {"ok": True, "items": []}
    def resolve(self, query): return {"ok": False}


class FakeWeb:
    def search(self, query, limit=4): return {"ok": True, "items": []}


def check(name, cond, detail=""):
    if not cond:
        raise AssertionError(f"{name}: {detail}")
    print("[OK]", name)


def main():
    with tempfile.TemporaryDirectory() as raw:
        td = Path(raw)
        skills = SkillStore(td / "skills")
        engine = CapabilityAcquisitionEngine(
            td / "acquisition.db",
            models=FakeModels(),
            skills=skills,
            apprenticeship=FakeApprenticeship(),
            actions=FakeActions(),
            workflows=EmptyWorkflows(),
            capabilities=FakeCapabilities(),
            public_data=FakePublicData(),
            services=FakeServices(),
            web_search=FakeWeb(),
            improvements=None,
            config={"acquisition_existing_score": 0.9},
        )

        result = engine.discover("automatizar o envio mensal de um relatório")
        check("Gap created", result.get("gap_id"), result)
        check("Recipe candidate created", any(x.get("kind") == "recipe" for x in result.get("candidates", [])), result)

        recipe = next(x for x in result["candidates"] if x["kind"] == "recipe")
        tested = engine.test_candidate(recipe["id"])
        check("Recipe validates", tested.get("ok"), tested)
        check("Missing action params became inputs", bool(tested["test"].get("inputs")), tested)

        installed = engine.install_candidate(recipe["id"])
        check("Recipe installs as Skill", installed.get("ok"), installed)
        skill = skills.get_skill(installed.get("installed_id"))
        check("Acquired Skill persists", bool(skill), installed)
        check("Acquisition provenance persists", skill.get("metadata", {}).get("acquired_by") == "CapabilityAcquisitionEngine", skill)

        url_result = engine.discover("consultar uma API de exemplo", source_url="https://example.com")
        api_candidate = next((x for x in url_result.get("candidates", []) if x.get("kind") == "openapi_import"), None)
        check("OpenAPI candidate discovered", bool(api_candidate), url_result)
        check("OpenAPI candidate validates", engine.test_candidate(api_candidate["id"]).get("ok"), api_candidate)

        failure = engine.record_failure("usar uma ferramenta completamente inexistente", "executor ausente")
        check("Failure creates capability gap", failure.get("recorded"), failure)

        cmd = parse_acquisition_command("Aprenda sozinho a fazer conciliação dos dados")
        check("Self-learning command parsed", cmd and cmd.get("auto_install") is True, cmd)
        cmd = parse_acquisition_command("Descubra como fazer conciliação dos dados")
        check("Discovery command does not auto-install", cmd and cmd.get("auto_install") is False, cmd)

        stats = engine.stats()
        check("Acquisition stats available", "gaps" in stats and "candidates" in stats, stats)

        print("\nCapability Acquisition test concluído.")


if __name__ == "__main__":
    main()
