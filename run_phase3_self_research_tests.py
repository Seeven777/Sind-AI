import json
from acquisition.self_research import SelfResearchLearner


class FakeResearch:
    def evidence_pack(self, query, limit=5, official_first=False):
        return {
            "ok": True,
            "cards": [{
                "title": "Documentação oficial",
                "url": "https://faq.whatsapp.com/example",
                "source_type": "official",
                "official": True,
                "authority_score": 90,
                "sentences": [
                    "O recurso permite iniciar uma conversa usando um número em formato internacional.",
                    "Um link HTTPS pode abrir a conversa no WhatsApp Web.",
                ],
            }],
        }


class FakeModels:
    def __init__(self, payload):
        self.payload = payload

    def chat(self, *args, **kwargs):
        return {"message": {"content": json.dumps(self.payload, ensure_ascii=False)}}


def good():
    return {
        "ready": True,
        "name": "enviar mensagem whatsapp pesquisado",
        "description": "Tenta abrir uma conversa e enviar uma mensagem.",
        "risk": "write",
        "inputs": {
            "numero": {"required": True, "description": "Número internacional"},
            "mensagem": {"required": True, "description": "Mensagem"},
        },
        "example_inputs": {"numero": "5511999999999", "mensagem": "teste"},
        "steps": [
            {"tool": "open_url", "args": {"url": "https://wa.me/{{numero}}"}},
            {"tool": "select_window", "args": {"query": "WhatsApp"}},
            {"tool": "inspect_selected_window", "args": {}},
            {"tool": "type_text", "args": {"text": "{{mensagem}}"}},
            {"tool": "press_key", "args": {"key": "enter"}},
        ],
        "verification": {
            "mode": "best_effort",
            "expected": "a mensagem aparecer na conversa",
        },
    }


def test_research_to_skill():
    learner = SelfResearchLearner(FakeResearch(), FakeModels(good()), {})
    out = learner.learn(
        "enviar uma mensagem para 5511999999999 com o texto teste",
        research_query="enviar mensagem WhatsApp",
    )
    assert out["ok"]
    assert out["risk"] == "write"
    assert out["sources"][0]["official"] is True


def test_reject_shell():
    data = good()
    data["steps"] = [{"tool": "powershell", "args": {"command": "x"}}]
    learner = SelfResearchLearner(FakeResearch(), FakeModels(data), {})
    out = learner.learn("teste", research_query="teste")
    assert not out["ok"]
    assert any("não é permitida" in x for x in out["issues"])


def test_reject_http():
    data = good()
    data["steps"][0] = {"tool": "open_url", "args": {"url": "http://localhost/admin"}}
    learner = SelfResearchLearner(FakeResearch(), FakeModels(data), {})
    out = learner.learn("teste", research_query="teste")
    assert not out["ok"]
    assert any("HTTPS público" in x for x in out["issues"])


def test_reject_unsafe_key():
    data = good()
    data["steps"][-1] = {"tool": "press_key", "args": {"key": "ctrl+alt+delete"}}
    learner = SelfResearchLearner(FakeResearch(), FakeModels(data), {})
    out = learner.learn("teste", research_query="teste")
    assert not out["ok"]
    assert any("lista segura" in x for x in out["issues"])


def test_force_write_for_external_effect():
    data = good()
    data["risk"] = "act"
    learner = SelfResearchLearner(FakeResearch(), FakeModels(data), {})
    out = learner.learn("teste", research_query="teste")
    assert out["ok"]
    assert out["risk"] == "write"


if __name__ == "__main__":
    funcs = [
        test_research_to_skill,
        test_reject_shell,
        test_reject_http,
        test_reject_unsafe_key,
        test_force_write_for_external_effect,
    ]
    for fn in funcs:
        fn()
        print(f"[OK] {fn.__name__}")
    print(f"\n{len(funcs)}/{len(funcs)} testes passaram.")
