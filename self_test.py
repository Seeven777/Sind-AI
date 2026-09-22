import json
import tempfile
from pathlib import Path

from actions.hub import ActionHub
from browser_agent.engine import BrowserAgent
from capabilities.hub import CapabilityHub
from content_studio.engine import ContentStudio
from knowledge.base import KnowledgeBase
from memory.store import MemoryStore
from observe.engine import ObservationEngine
from runtime.task_store import TaskStore
from skills.store import SkillStore
from website.inspector import WebsiteInspector
from wordpress.manager import WordPressManager
from workflows.hub import WorkflowHub
from runtime.intent_router import parse_fast_intent
from web_search.engine import PublicWebSearch
from research.engine import ResearchEngine
from research.source_resolver import normalize_url
from document_intelligence.engine import DocumentIntelligence
from workspace_intelligence.engine import WorkspaceIntelligence
from supervisor.engine import RuntimeSupervisor
from runtime.diagnostics import RuntimeDiagnostics

BASE = Path(__file__).resolve().parent


def check(name, condition, detail=""):
    if not condition:
        raise AssertionError(f"{name}: {detail}")
    print(f"[OK] {name}")


def main():
    with tempfile.TemporaryDirectory() as td_raw:
        td = Path(td_raw)

        # Public Capability Hub from 0.6+
        cap = CapabilityHub(
            BASE / "capabilities" / "catalog.json",
            td / "cap_cache",
            td / "user_capabilities.json",
        )
        cap_stats = cap.stats()
        check("Capability Hub >= 200", cap_stats["capabilities"] >= 200, cap_stats)

        # Engines for new Action Hub. Browser is instantiated but not launched.
        browser = BrowserAgent(td / "browser_profile", td / "downloads")
        website = WebsiteInspector()
        content = ContentStudio()
        knowledge = KnowledgeBase(td / "knowledge.db", td / "knowledge_storage")
        wordpress = WordPressManager(td / "wordpress_profiles.json")
        observe = ObservationEngine(td / "observe")
        websearch = PublicWebSearch()
        research = ResearchEngine(websearch, td / "research_history")
        docs_root = td / "docs"
        docs_root.mkdir()
        document = DocumentIntelligence(docs_root)
        workspace = WorkspaceIntelligence(td)
        tasks_for_supervisor = TaskStore(td / "supervisor_tasks.db")
        diagnostics = RuntimeDiagnostics(td / "logs")
        supervisor = RuntimeSupervisor(
            config={"model":"qwen3:4b","num_ctx":4096,"agent_llm_timeout_seconds":40,"agent_total_timeout_seconds":105,"agent_max_rounds":4,"agent_max_tool_calls":10},
            persistent_root=td, workspace=td, tasks=tasks_for_supervisor, diagnostics=diagnostics, browser=browser,
            ollama_url="http://127.0.0.1:11434/api/chat", base_dir=BASE,
        )

        actions = ActionHub(
            BASE / "actions" / "catalog.json",
            {
                "browser": browser,
                "website": website,
                "content": content,
                "knowledge": knowledge,
                "wordpress": wordpress,
                "observe": observe,
                "websearch": websearch,
                "research": research,
                "document": document,
                "workspace": workspace,
                "supervisor": supervisor,
            },
        )
        stats = actions.stats()
        check("Action Hub >= 300 ações", stats["actions"] >= 300, stats)
        check("Action Hub >= 11 engines", len(stats["engines"]) >= 11, stats["engines"])

        workflows = WorkflowHub(BASE / "workflows" / "catalog.json", actions)
        wf_stats = workflows.stats()
        check("Workflow Hub >= 300 workflows", wf_stats["workflows"] >= 300, wf_stats)
        wf_search = workflows.search("seo", limit=10)
        check("Busca Workflow Hub", wf_search["ok"] and wf_search["count"] >= 1, wf_search)
        wf_exec = workflows.execute("workflow.content.metrics_basic", {"text":"Teste de texto para o Jarvis."})
        check("Workflow composto executa", wf_exec["ok"] and wf_exec["steps"] >= 3, wf_exec)

        fast = parse_fast_intent("Abra o Google e pesquise sobre NR-1")
        check("Fast intent Google search", fast and fast.get("kind") == "open_search" and "NR-1" in fast.get("url", ""), fast)

        catalog = json.loads((BASE/"actions"/"catalog.json").read_text(encoding="utf-8"))["actions"]
        ids = [x["id"] for x in catalog]
        check("IDs de ações únicos", len(ids) == len(set(ids)), len(ids))

        check("Browser Agent >= 40 ações", stats["engines"].get("browser",0) >= 40)
        check("Website Inspector >= 40 ações", stats["engines"].get("website",0) >= 40)
        check("Content Studio >= 60 ações", stats["engines"].get("content",0) >= 60)
        check("WordPress >= 40 ações", stats["engines"].get("wordpress",0) >= 40)

        found = actions.search("wordpress criar rascunho post", limit=10)
        check("Busca Action Hub", found["ok"] and any(x["id"]=="wordpress.posts.create_draft" for x in found["items"]))

        result = actions.execute("content.slugify", {"text":"Auxílio Creche na Convenção Coletiva"})
        check("Content Studio executa", result["ok"] and result["text"]=="auxilio-creche-na-convencao-coletiva", result)

        result = actions.execute("content.meta_title_check", {"text":"Direitos previstos na Convenção Coletiva"})
        check("SEO utility executa", result["ok"] and "chars" in result, result)

        # Research Engine: URL real e síntese determinística sem rede.
        bing = "https://www.bing.com/ck/a?!&&u=a1aHR0cHM6Ly93d3cuZ292LmJyL3RyYWJhbGhvLWUtZW1wcmVnby9wdC1ici9hY2Vzc28tYS1pbmZvcm1hY2FvL3BhcnRpY2lwYWNhby1zb2NpYWwvY29uc2VsaG9zLWUtb3JnYW9zLWNvbGVnaWFkb3MvY29taXNzYW8tdHJpcGFydGl0ZS1wYXJ0aXRhcmlhLXBlcm1hbmVudGUvbm9ybWFzLXJlZ3VsYW1lbnRhZG9yYS9ub3JtYXMtcmVndWxhbWVudGFkb3Jhcy12aWdlbnRlcy9uci0x&ntb=1"
        decoded = normalize_url(bing)
        check("Bing redirect vira URL real", decoded.startswith("https://www.gov.br/trabalho-e-emprego/"), decoded)
        fake_bundle = {"cards":[
            {"title":"NR-1 oficial","url":"https://www.gov.br/teste","domain":"gov.br","source_type":"governo","authority_score":115,"official":True,"sentences":["A NR-1 estabelece disposições gerais e requisitos para o gerenciamento de riscos ocupacionais."]},
            {"title":"Fonte técnica","url":"https://example.org/nr1","domain":"example.org","source_type":"organizacao","authority_score":62,"official":False,"sentences":["O gerenciamento de riscos é um eixo central do conteúdo analisado."]},
        ]}
        summary = research.deterministic_summary(fake_bundle)
        check("Research fallback produz síntese útil", "Pontos encontrados" in summary and "NR-1" in summary, summary)
        report = research.markdown_report("NR-1", fake_bundle, synthesis=None, synthesis_error="timeout")
        check("Research report usa URL final", "bing.com/ck" not in report and "https://www.gov.br/teste" in report, report[:600])

        # Document Intelligence.
        sample = docs_root / "amostra.txt"
        sample.write_text("Convenção Coletiva\n\nBenefícios e direitos do setor pet.\nNR-1 e segurança do trabalho.", encoding="utf-8")
        doc_extract = actions.execute("document.extract_text", {"path":str(sample)})
        check("Document Intelligence extrai texto", doc_extract["ok"] and "Convenção" in doc_extract["text"], doc_extract)
        doc_search = actions.execute("document.search", {"path":str(sample),"query":"NR-1"})
        check("Document Intelligence pesquisa", doc_search["ok"] and doc_search["count"] >= 1, doc_search)

        # Workspace + Supervisor locais.
        ws = actions.execute("workspace.summary", {})
        check("Workspace Intelligence", ws["ok"], ws)
        health = actions.execute("supervisor.quick_health", {})
        check("Runtime Supervisor quick health", health["ok"], health)

        # Knowledge Base
        ing = actions.execute("knowledge.ingest.text", {
            "collection":"sindpetshop",
            "title":"Teste CCT",
            "text":"A Convenção Coletiva pode prever benefícios adicionais aos trabalhadores do setor pet."
        })
        check("Knowledge ingest", ing["ok"], ing)
        search = actions.execute("knowledge.search", {
            "collection":"sindpetshop",
            "query":"Convenção Coletiva benefícios"
        })
        check("Knowledge search", search["ok"] and search["count"] >= 1, search)

        # Parametric skills
        skills = SkillStore(td/"skills")
        saved = skills.save_parametric_skill(
            "teste_parametrico",
            [{"tool":"create_file","args":{"path":"{{arquivo}}","content":"{{conteudo}}"}}],
            inputs={
                "arquivo":{"required":True},
                "conteudo":{"required":True}
            },
        )
        check("Skill parametrizada salva", saved["ok"], saved)
        rendered = skills.render_skill(
            skills.get_skill("teste_parametrico"),
            {"arquivo":"teste.txt","conteudo":"ABC"},
        )
        check("Skill parametrizada renderiza", rendered["ok"] and rendered["steps"][0]["args"]["content"]=="ABC", rendered)

        # Privacy of recorder can be checked without starting hooks.
        status = observe.status()
        check("Observe privacy flag", status["privacy"] == "typed_text_masked", status)

        # Legacy persistence components still healthy
        mem = MemoryStore(td/"memory.db")
        mem.remember("SindPetshop teste", key="teste")
        check("Memória persistente", bool(mem.relevant("SindPetshop")))

        tasks = TaskStore(td/"tasks.db")
        task_id = tasks.start("Teste de autonomia")
        tasks.set_plan(task_id, ["Pesquisar", "Executar", "Verificar"])
        tasks.event(task_id, 1, "search_actions", {"query":"browser"}, {"ok":True})
        tasks.advance_plan(task_id)
        tasks.finish(task_id, "ok")
        latest = tasks.recent(1)[0]
        check("Task runtime", latest["status"] == "completed")
        check("Task plan persistente", latest["plan"] == ["Pesquisar","Executar","Verificar"] and latest["current_step"] == 1)

        stale_id = tasks.start("Tarefa órfã")
        reconciled = tasks.reconcile_stale(stale_after_seconds=0, reason="teste")
        check("Tarefas órfãs são reconciliadas", reconciled["interrupted"] >= 1 and tasks.get(stale_id)["status"] == "interrupted", reconciled)

        combined = cap_stats["capabilities"] + stats["actions"]

        print("\nResumo:")
        print(json.dumps({
            "public_capabilities": cap_stats["capabilities"],
            "new_local_actions": stats["actions"],
            "new_composite_workflows": wf_stats["workflows"],
            "combined_brokered_capabilities": combined + wf_stats["workflows"],
            "action_engines": stats["engines"],
        }, ensure_ascii=False, indent=2))
        print("\nSelf-test offline concluído.")


if __name__ == "__main__":
    main()
