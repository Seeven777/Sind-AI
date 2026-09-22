import tempfile
from pathlib import Path

from attachments.manager import AttachmentManager
from cognitive.context_orchestrator import ContextOrchestrator
from cognitive.conversation_store import ConversationStore
from cognitive.learning import LearningJournal
from cognitive.project_store import ProjectStore
from cognitive.reflection import ReflectionEngine
from cognitive.semantic_memory import SemanticMemory
from hardware.profiler import HardwareProfiler
from institutional.services import InstitutionalServices
from knowledge.base import KnowledgeBase
from memory.store import MemoryStore
from self_improvement.queue import ImprovementQueue


BASE=Path(__file__).resolve().parent


def check(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    print("[OK]",name)


def main():
    with tempfile.TemporaryDirectory() as raw:
        td=Path(raw)

        conversations=ConversationStore(td/"conversations.db")
        learning=LearningJournal(td/"learning.db")
        memory=MemoryStore(td/"memory.db")
        semantic=SemanticMemory(td/"semantic.db","http://127.0.0.1:9","none",enabled=False)
        projects=ProjectStore(td/"projects.db")
        kb=KnowledgeBase(td/"knowledge.db",td/"storage")
        attachments=AttachmentManager(td/"attachments.db",kb,projects)
        reflections=ReflectionEngine(td/"reflections.db")
        improvements=ImprovementQueue(td/"improvements.db")
        services=InstitutionalServices(BASE/"data"/"institutional_services.json")

        # Projects
        p=projects.create("Campanha teste","Contexto persistente")
        check("Project create",p["ok"],p)
        pid=p["data"]["id"]
        projects.link_session(pid,conversations.current_session_id)
        projects.add_note(pid,"Objetivo","Criar conteúdo voltado a direitos do trabalhador.")
        ctx=projects.context("direitos")
        check("Project context", "direitos" in ctx["text"].lower(),ctx)

        # Attachments -> KB
        file=td/"manual.txt"
        file.write_text("Procedimento interno de homologação e atendimento ao trabalhador.",encoding="utf-8")
        ar=attachments.add_files([str(file)],session_id=conversations.current_session_id,project_id=pid)
        check("Attachment ingest",ar["ok"],ar)
        found=attachments.search_context("homologação",session_id=conversations.current_session_id,project_id=pid)
        check("Attachment retrieval",found["items"],found)

        # Explicit learning and reflection
        lesson=learning.learn_from_user("Prefiro fontes oficiais antes de blogs")
        check("Learning journal",lesson.get("learned"),lesson)
        for _ in range(3):
            last=reflections.reflect("crie publicação sobre direitos", "ok", status="completed")
        candidates=reflections.list(kind="skill_candidate")
        check("Repeated pattern -> skill candidate",candidates["count"]>=1,candidates)

        fail=reflections.reflect("tarefa complexa qualquer","timeout",status="failed")
        check("Failure reflection",bool(fail["reflection_ids"]),fail)
        imp=improvements.propose("runtime_failure","Timeout observado","Criar fallback mais rápido",{"error":"timeout"},70)
        check("Improvement proposal",imp["ok"],imp)

        # Institutional services
        s=services.resolve("instagram")
        check("Instagram service resolved",s["ok"] and s["data"]["id"]=="instagram",s)
        s=services.resolve("dashboard")
        check("Insights dashboard resolved",s["ok"] and s["data"]["id"]=="insights_dashboard",s)
        cmd=services.parse_open_command("Abra o Slack do sindicato")
        check("Daily service fast command",cmd and cmd["service"]=="slack",cmd)
        check("Daily services mapped",services.stats()["services"]>=9,services.stats())

        # Context fusion
        conversations.append("user","Estamos trabalhando em uma campanha de direitos.")
        conversations.append("assistant","Vou manter o foco em direitos.")
        memory.remember("Priorizar fontes oficiais para pesquisas.")
        orchestrator=ContextOrchestrator(
            conversations,learning,memory,semantic,projects,attachments,services=services
        )
        bundle=orchestrator.build("direitos homologação",max_chars=5000)
        check("Context orchestrator project", "PROJETO ATUAL" in bundle["text"],bundle["text"])
        check("Context orchestrator attachment", "homolog" in bundle["text"].lower(),bundle["text"])

        # Hardware profile must never fail even when GPU tools are absent.
        hw=HardwareProfiler().profile()
        check("Hardware profiler",hw["ok"] and hw["tier"] in {"lite","standard","power"},hw)

        print("\nPersonal GPT 1.0 test concluído.")


if __name__=="__main__":
    main()
