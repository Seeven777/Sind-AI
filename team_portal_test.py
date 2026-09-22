import tempfile
from pathlib import Path

from knowledge.base import KnowledgeBase
from team_assistant.engine import TeamAssistantEngine
from team_assistant.portal.server import TeamPortalApp


def check(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    print(f"[OK] {name}")


def main():
    with tempfile.TemporaryDirectory() as raw:
        td=Path(raw)
        team=TeamAssistantEngine(td/"team.db")
        kb=KnowledgeBase(td/"knowledge.db",td/"knowledge_storage")

        role=team.role_create("atendimento","Atendimento interno")
        check("Role criada",role["ok"],role)
        role_id=role["data"]["id"]

        user=team.user_create("colaborador","Colaborador Teste",role_id=role_id,password="Teste#1234")
        check("Usuário criado",user["ok"],user)
        auth=team.authenticate("colaborador","Teste#1234")
        check("Autenticação local",auth["ok"],auth)

        ing=kb.ingest_text(
            "manual_interno",
            "Procedimento de teste",
            "Para localizar um procedimento interno, consulte a base autorizada e siga as etapas documentadas.",
            source="teste"
        )
        check("Knowledge ingest",ing["ok"],ing)
        team.collection_grant_set(role_id,"manual_interno","read")

        app=TeamPortalApp(team,kb,training=None,ollama_url="http://127.0.0.1:9/api/chat",model="qwen3:4b")
        dashboard=app.dashboard(auth["user"])
        check("Dashboard",dashboard["ok"],dashboard)
        check("Collection grant applied","manual_interno" in dashboard["collections"],dashboard)

        evidence=app.evidence(auth["user"],"procedimento interno",max_sources=4)
        check("Grounding evidence",len(evidence)>=1,evidence)

        # Porta impossível força fallback sem depender de Ollama.
        answer=app.answer(auth["user"],"Como localizar um procedimento interno?")
        check("Answer fallback remains grounded",answer["ok"] and answer["grounded"] and answer.get("fallback"),answer)
        check("Source citation returned",bool(answer.get("sources")),answer)

        unanswered=app.answer(auth["user"],"zzzz assunto completamente ausente qqqq")
        check("Unsupported question does not hallucinate",unanswered["ok"] and not unanswered["grounded"],unanswered)
        gaps=team.gap_list(status="open")
        check("Knowledge gap registered",gaps["count"]>=1,gaps)

        print("\nTeam Portal offline test concluído.")


if __name__=="__main__":
    main()
