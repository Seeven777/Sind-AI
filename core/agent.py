import json
import re
import threading
import time
from datetime import datetime
from pathlib import Path

from core.ollama_client import OllamaClient
from core.router import fast_path
from memory.commands import parse_memory_command
from memory.store import MemoryStore
from skills.commands import parse_skill_command
from skills.store import SkillStore
from access.commands import parse_access_command
from access.controller import DeepAccessController
from capabilities.commands import parse_capability_command
from capabilities.hub import CapabilityHub
from capabilities.public_web import fetch_public_url, read_rss
from runtime.task_store import TaskStore
from runtime.pattern_miner import PatternMiner
from runtime.commands import parse_task_command
from runtime.data_vault import backup_data
from actions.commands import parse_action_command
from actions.hub import ActionHub
from browser_agent.engine import BrowserAgent
from website.inspector import WebsiteInspector
from content_studio.engine import ContentStudio
from knowledge.base import KnowledgeBase
from wordpress.manager import WordPressManager
from observe.engine import ObservationEngine
from web_search.engine import PublicWebSearch
from runtime.verifier import ResultVerifier
from runtime.world_state import snapshot as world_snapshot
from runtime.intent_router import parse_fast_intent
from runtime.diagnostics import RuntimeDiagnostics
from workflows.hub import WorkflowHub
from workflows.commands import parse_workflow_command
from research.engine import ResearchEngine
from document_intelligence.engine import DocumentIntelligence
from supervisor.engine import RuntimeSupervisor
from workspace_intelligence.engine import WorkspaceIntelligence
from institutional.store import InstitutionalStore
from institutional.services import InstitutionalServices
from institutional.service_runtime import InstitutionalServiceRuntime
from institutional_knowledge.engine import InstitutionalKnowledge
from training.engine import TrainingEngine
from content_ops.engine import ContentOps
from governance.engine import GovernanceEngine
from automations.engine import AutomationEngine
from monitors.engine import MonitorEngine
from approvals.engine import ApprovalEngine
from connectors.gateway import ConnectorGateway
from team_assistant.engine import TeamAssistantEngine
from notifications.engine import NotificationEngine
from cognitive.conversation_store import ConversationStore
from cognitive.learning import LearningJournal
from cognitive.semantic_memory import SemanticMemory
from cognitive.model_router import AdaptiveModelRouter
from cognitive.answer_engine import ConversationalAnswerEngine
from cognitive.project_store import ProjectStore
from cognitive.reflection import ReflectionEngine
from cognitive.context_orchestrator import ContextOrchestrator
from cognitive.self_awareness import SelfAwareness
from attachments.manager import AttachmentManager
from self_improvement.queue import ImprovementQueue
from hardware.profiler import HardwareProfiler
from public_data.engine import PublicDataEngine
from swarm.registry import AgentRegistry
from swarm.blackboard import SwarmBlackboard
from swarm.apprenticeship import ApprenticeshipEngine
from swarm.orchestrator import SwarmOrchestrator
from swarm.demonstration import DemonstrationTeacher
from acquisition.engine import CapabilityAcquisitionEngine
from acquisition.commands import parse_acquisition_command
from long_horizon.engine import LongHorizonEngine
from long_horizon.commands import parse_long_horizon_command

from tools.apps import open_app, open_folder
from tools.browser import open_url
from tools.clipboard import get_clipboard_text, set_clipboard_text
from tools.files import FileTools
from tools.screen import take_screenshot
from tools.windows import list_processes, list_windows
from tools.windows_paths import get_desktop_path


class JarvisAgent:
    def __init__(self, config, base_dir=None):
        self.config = config
        self.base_dir = Path(base_dir or Path.cwd()).resolve()
        # Model/tool execution is serialized on the CPU-first reference hardware.
        # Background jobs release the lock between checkpoints/steps.
        self._execution_lock = threading.RLock()

        self.home = Path.home().resolve()
        self.desktop = get_desktop_path()
        self.workspace = (self.home / config["workspace_name"]).resolve()
        self.workspace.mkdir(parents=True, exist_ok=True)

        self.screenshot_dir = self.workspace / config.get(
            "screenshot_folder",
            "Screenshots"
        )

        self.files = FileTools([self.home], self.workspace)

        # Dados aprendidos ficam fora da pasta da versão. Assim, novas releases
        # podem ser extraídas em outra pasta sem zerar memória, skills e histórico.
        persistent_name = config.get("persistent_root_name", "JarvisData")
        self.persistent_root = (self.home / persistent_name).resolve()
        self.persistent_root.mkdir(parents=True, exist_ok=True)

        def persistent_path(relative_value, fallback):
            raw = Path(config.get(relative_value, fallback))
            if raw.is_absolute():
                path = raw
            else:
                path = self.persistent_root / raw
            path.parent.mkdir(parents=True, exist_ok=True)
            return path.resolve()

        memory_db = persistent_path("memory_db", "memory/jarvis_memory.db")
        self.memory = MemoryStore(memory_db)

        skills_dir = persistent_path("skills_dir", "skills")
        skills_dir.mkdir(parents=True, exist_ok=True)
        self.skills = SkillStore(skills_dir)
        self.deep_access = DeepAccessController()

        # Catálogo nativo acompanha a release; catálogo aprendido é persistente.
        catalog_path = self.base_dir / self.config.get("capability_catalog", "capabilities/catalog.json")
        user_catalog_path = persistent_path("capability_user_catalog", "capabilities/user_capabilities.json")
        cache_dir = persistent_path("capability_cache_folder", "cache/CapabilityCache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        self.capabilities = CapabilityHub(
            catalog_path=catalog_path,
            cache_dir=cache_dir,
            user_catalog_path=user_catalog_path,
            user_agent="JarvisSindPet/0.6 (+local-assistant)",
        )

        tasks_db = persistent_path("tasks_db", "tasks/jarvis_tasks.db")
        self.tasks = TaskStore(tasks_db)
        self.pattern_miner = PatternMiner(self.skills.action_log)

        diagnostics_dir = persistent_path("diagnostics_dir", "logs")
        diagnostics_dir.mkdir(parents=True, exist_ok=True)
        self.diagnostics = RuntimeDiagnostics(diagnostics_dir)

        # A inicialização não possui worker legítimo anterior. Tarefas que ficaram
        # RUNNING/RETRYING em outra execução são reconciliadas como INTERRUPTED.
        reconciliation = self.tasks.reconcile_stale(
            stale_after_seconds=int(self.config.get("startup_stale_task_seconds", 1)),
            reason="Sessão anterior do Jarvis foi encerrada antes da conclusão da tarefa.",
        )
        if reconciliation.get("interrupted"):
            self.diagnostics.event("startup_task_reconciliation", **reconciliation)

        # Engines locais. Permanência e perfis ficam fora da pasta da release.
        browser_profile = persistent_path("browser_profile_dir", "browser/profile")
        browser_downloads = self.workspace / "JarvisDownloads"
        browser_downloads.mkdir(parents=True, exist_ok=True)
        self.browser_agent = BrowserAgent(browser_profile, browser_downloads)

        self.website_inspector = WebsiteInspector(user_agent="JarvisSindPet/0.7 (+local-assistant)")
        self.content_studio = ContentStudio()

        knowledge_db = persistent_path("knowledge_db", "knowledge/knowledge.db")
        knowledge_storage = persistent_path("knowledge_storage_dir", "knowledge/storage")
        knowledge_storage.mkdir(parents=True, exist_ok=True)
        self.knowledge = KnowledgeBase(knowledge_db, knowledge_storage)

        wordpress_profiles = persistent_path("wordpress_profiles", "wordpress/profiles.json")
        self.wordpress = WordPressManager(wordpress_profiles)

        observe_root = persistent_path("observe_root", "observe")
        observe_root.mkdir(parents=True, exist_ok=True)
        self.observe = ObservationEngine(observe_root)
        self.web_search = PublicWebSearch(user_agent="JarvisSindPet/0.7.3 (+local-assistant)", browser_fallback=self.browser_agent)

        research_history = persistent_path("research_history_dir", "research")
        research_history.mkdir(parents=True, exist_ok=True)
        self.research = ResearchEngine(self.web_search, history_dir=research_history)
        self.documents = DocumentIntelligence(allowed_root=self.home)
        self.workspace_intelligence = WorkspaceIntelligence(self.workspace)

        institutional_db = persistent_path("institutional_db", "institutional/institutional.db")
        self.institutional = InstitutionalStore(institutional_db)
        self.services = InstitutionalServices(self.base_dir / "data" / "institutional_services.json")
        institutional_knowledge_db = persistent_path("institutional_knowledge_db", "knowledge/institutional.db")
        self.institutional_knowledge = InstitutionalKnowledge(
            institutional_knowledge_db, self.knowledge, self.documents, self.workspace
        )
        training_db = persistent_path("training_db", "training/training.db")
        self.training = TrainingEngine(training_db, knowledge_engine=self.institutional_knowledge)
        content_ops_db = persistent_path("content_ops_db", "content/content_ops.db")
        self.content_ops = ContentOps(content_ops_db, self.workspace, institutional_store=self.institutional)
        governance_db = persistent_path("governance_db", "governance/governance.db")
        self.governance = GovernanceEngine(governance_db)

        notifications_db = persistent_path("notifications_db", "notifications/notifications.db")
        self.notifications = NotificationEngine(notifications_db)
        approvals_db = persistent_path("approvals_db", "approvals/approvals.db")
        self.approvals = ApprovalEngine(approvals_db)
        connectors_db = persistent_path("connectors_db", "connectors/connectors.db")
        self.connectors = ConnectorGateway(connectors_db)
        team_db = persistent_path("team_db", "team/team.db")
        self.team = TeamAssistantEngine(team_db)
        monitors_db = persistent_path("monitors_db", "monitors/monitors.db")
        self.monitors = MonitorEngine(monitors_db, knowledge=self.knowledge, wordpress=self.wordpress)
        automations_db = persistent_path("automations_db", "automations/automations.db")
        self.automations = AutomationEngine(
            automations_db, poll_seconds=self.config.get("automation_poll_seconds", 5)
        )

        # Cognitive Core: conversa persistente, aprendizado por correção e broker de dados públicos.
        conversation_db = persistent_path("conversation_db", "cognitive/conversations.db")
        learning_db = persistent_path("learning_db", "cognitive/learning.db")
        public_proposals = persistent_path("public_data_proposals", "public_data/proposals.json")
        self.conversations = ConversationStore(conversation_db)
        self.learning = LearningJournal(learning_db)
        semantic_db = persistent_path("semantic_memory_db", "cognitive/semantic.db")
        self.semantic = SemanticMemory(
            semantic_db, self.config.get("ollama_url", "http://127.0.0.1:11434"),
            self.config.get("embedding_model", "nomic-embed-text-v2-moe"),
            enabled=bool(self.config.get("semantic_memory_enabled", False)),
        )
        self.public_data = PublicDataEngine(
            self.base_dir / "public_data" / "registry.json", public_proposals,
            user_agent="JarvisLocal/1.0 (+personal-gpt)",
        )

        # Personal GPT layer: projetos, anexos, reflexão e autoevolução supervisionada.
        projects_db = persistent_path("projects_db", "cognitive/projects.db")
        reflections_db = persistent_path("reflections_db", "cognitive/reflections.db")
        improvements_db = persistent_path("improvements_db", "cognitive/improvements.db")
        attachments_db = persistent_path("attachments_db", "cognitive/attachments.db")
        self.projects = ProjectStore(projects_db)
        self.reflections = ReflectionEngine(reflections_db)
        self.improvements = ImprovementQueue(improvements_db)
        self.attachments = AttachmentManager(attachments_db, self.knowledge, self.projects)
        swarm_blackboard_db = persistent_path("swarm_blackboard_db", "cognitive/swarm_blackboard.db")
        apprenticeship_db = persistent_path("apprenticeship_db", "cognitive/apprenticeship.db")
        acquisition_db = persistent_path("acquisition_db", "cognitive/capability_acquisition.db")
        self.hardware = HardwareProfiler()
        self.context_orchestrator = ContextOrchestrator(
            self.conversations, self.learning, self.memory, self.semantic,
            self.projects, self.attachments, services=self.services
        )

        actions_catalog = self.base_dir / self.config.get("action_catalog", "actions/catalog.json")
        self.actions = ActionHub(
            actions_catalog,
            engines={
                "browser": self.browser_agent,
                "website": self.website_inspector,
                "content": self.content_studio,
                "knowledge": self.knowledge,
                "wordpress": self.wordpress,
                "observe": self.observe,
                "websearch": self.web_search,
                "research": self.research,
                "document": self.documents,
                "workspace": self.workspace_intelligence,
                "institutional": self.institutional,
                "institutional_knowledge": self.institutional_knowledge,
                "training": self.training,
                "content_ops": self.content_ops,
                "governance": self.governance,
                "automations": self.automations,
                "monitors": self.monitors,
                "approvals": self.approvals,
                "connectors": self.connectors,
                "team": self.team,
                "notifications": self.notifications,
                "public_data": self.public_data,
            },
        )
        workflows_catalog = self.base_dir / self.config.get("workflow_catalog", "workflows/catalog.json")
        self.workflows = WorkflowHub(workflows_catalog, self.actions)

        self.ollama = OllamaClient(
            config["ollama_url"],
            config["model"],
            config.get("num_ctx", 4096),
            config.get("temperature", 0.1),
        )
        self.models = AdaptiveModelRouter(
            self.ollama,
            fast_model=config.get("fast_model", "qwen3:1.7b"),
            reasoning_model=config.get("reasoning_model", config.get("model", "qwen3:4b")),
            fast_timeout=config.get("fast_model_timeout_seconds", 18),
            reasoning_timeout=config.get("agent_llm_timeout_seconds", 40),
            fallback_timeout=config.get("fast_model_fallback_timeout_seconds", 22),
        )
        self.swarm_registry = AgentRegistry()
        self.swarm_blackboard = SwarmBlackboard(swarm_blackboard_db)
        self.apprenticeship = ApprenticeshipEngine(apprenticeship_db, models=self.models)
        self.swarm = SwarmOrchestrator(
            self.models, self.swarm_registry, self.swarm_blackboard,
            apprenticeship=self.apprenticeship, config=self.config
        )
        self.demonstration_teacher = DemonstrationTeacher(self.observe, self.skills)
        self.acquisition = CapabilityAcquisitionEngine(
            acquisition_db,
            models=self.models,
            skills=self.skills,
            apprenticeship=self.apprenticeship,
            actions=self.actions,
            workflows=self.workflows,
            capabilities=self.capabilities,
            public_data=self.public_data,
            services=self.services,
            web_search=self.web_search,
            improvements=self.improvements,
            config=self.config,
        )
        long_horizon_db = persistent_path("long_horizon_db", "cognitive/long_horizon.db")
        self.long_horizon = LongHorizonEngine(long_horizon_db, config=self.config)
        self.long_horizon.set_planner(self._plan_long_horizon_job)
        self.long_horizon.set_executor(self._execute_long_horizon_step)
        self.long_horizon.set_notifier(self._long_horizon_notification)
        self.self_awareness = SelfAwareness(
            self.services, self.actions, self.workflows, self.capabilities,
            self.models, self.hardware, self.knowledge, connectors=self.connectors,
            swarm=self.swarm, apprenticeship=self.apprenticeship,
            demonstration=self.demonstration_teacher,
            acquisition=self.acquisition,
            long_horizon=self.long_horizon,
        )
        self.service_runtime = InstitutionalServiceRuntime(
            self.services, self.browser_agent, self.models
        )
        self.conversation_answer = ConversationalAnswerEngine(
            self.models,
            self.conversations,
            self.learning,
            self.institutional,
            self.institutional_knowledge,
            self.web_search,
            context_orchestrator=self.context_orchestrator,
            public_data=self.public_data,
        )

        self.supervisor = RuntimeSupervisor(
            config=self.config,
            persistent_root=self.persistent_root,
            workspace=self.workspace,
            tasks=self.tasks,
            diagnostics=self.diagnostics,
            browser=self.browser_agent,
            ollama_url=self.config.get("ollama_url"),
            base_dir=self.base_dir,
        )
        # Supervisor entra no broker somente após estar construído.
        self.actions.engines["supervisor"] = self.supervisor

        # Operações autônomas e colaboração.
        self.approvals.set_executor(self._execute_approved_item)
        self.approvals.set_resolution_callback(self._approval_resolution)
        self.automations.set_executor(self._execute_automation_job)
        self.automations.set_approval_callback(self._automation_needs_approval)
        self.automations.set_notifier(self._automation_notification)
        self.monitors.set_notifier(self._monitor_notification)
        if self.config.get("automation_enabled", True):
            self.automations.start_worker()

        self.history = []
        self._last_response_metadata = {}
        self._executing_skill = False
        self._active_task_id = None
        self._cancel_event = threading.Event()
        self.verifier = ResultVerifier(self.files)

        self.tools_schema = [
            {"type":"function","function":{"name":"create_folder","description":"Cria pasta. O path pode ser um alias aprendido.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
            {"type":"function","function":{"name":"list_files","description":"Lista arquivos/pastas. O path pode ser um alias aprendido.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
            {"type":"function","function":{"name":"search_files","description":"Procura por nome.","parameters":{"type":"object","properties":{"root":{"type":"string"},"query":{"type":"string"}},"required":["root","query"]}}},
            {"type":"function","function":{"name":"create_file","description":"Cria arquivo texto.","parameters":{"type":"object","properties":{"path":{"type":"string"},"content":{"type":"string"}},"required":["path","content"]}}},
            {"type":"function","function":{"name":"read_file","description":"Lê arquivo texto.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
            {"type":"function","function":{"name":"rename_item","description":"Renomeia arquivo/pasta.","parameters":{"type":"object","properties":{"path":{"type":"string"},"new_name":{"type":"string"}},"required":["path","new_name"]}}},
            {"type":"function","function":{"name":"copy_item","description":"Copia arquivo/pasta.","parameters":{"type":"object","properties":{"source":{"type":"string"},"destination":{"type":"string"}},"required":["source","destination"]}}},
            {"type":"function","function":{"name":"move_item","description":"Move arquivo/pasta.","parameters":{"type":"object","properties":{"source":{"type":"string"},"destination":{"type":"string"}},"required":["source","destination"]}}},
            {"type":"function","function":{"name":"delete_item","description":"Exclui arquivo/pasta. Requer confirmação.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
            {"type":"function","function":{"name":"open_folder","description":"Abre pasta.","parameters":{"type":"object","properties":{"path":{"type":"string"}},"required":["path"]}}},
            {"type":"function","function":{"name":"open_app","description":"Abre app permitido.","parameters":{"type":"object","properties":{"app":{"type":"string"}},"required":["app"]}}},
            {"type":"function","function":{"name":"open_url","description":"Abre site.","parameters":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}},
            {"type":"function","function":{"name":"get_clipboard","description":"Lê clipboard.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"set_clipboard","description":"Escreve clipboard.","parameters":{"type":"object","properties":{"text":{"type":"string"}},"required":["text"]}}},
            {"type":"function","function":{"name":"take_screenshot","description":"Tira screenshot.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"list_windows","description":"Lista janelas abertas.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"list_processes","description":"Lista processos.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"select_window","description":"Seleciona uma janela aberta pelo título para automação controlada.","parameters":{"type":"object","properties":{"query":{"type":"string"}},"required":["query"]}}},
            {"type":"function","function":{"name":"inspect_selected_window","description":"Lê os controles UI Automation da janela selecionada.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"click_control","description":"Aciona um controle visível pelo nome na janela selecionada.","parameters":{"type":"object","properties":{"name":{"type":"string"},"control_type":{"type":"string"}},"required":["name"]}}},
            {"type":"function","function":{"name":"type_text","description":"Digita texto na janela selecionada ou em um campo específico. Não usar para senhas/segredos.","parameters":{"type":"object","properties":{"text":{"type":"string"},"control_name":{"type":"string"},"clear_first":{"type":"boolean"}},"required":["text"]}}},
            {"type":"function","function":{"name":"press_key","description":"Pressiona uma tecla segura na janela selecionada.","parameters":{"type":"object","properties":{"key":{"type":"string"}},"required":["key"]}}},
            {"type":"function","function":{"name":"fetch_public_url","description":"Lê uma URL HTTPS pública fornecida ou encontrada, extraindo texto/JSON sem abrir o navegador.","parameters":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}},
            {"type":"function","function":{"name":"read_rss","description":"Lê um feed RSS/Atom HTTPS público e retorna itens recentes.","parameters":{"type":"object","properties":{"url":{"type":"string"},"limit":{"type":"integer"}},"required":["url"]}}},
            {"type":"function","function":{"name":"search_capabilities","description":"Pesquisa no Capability Hub por uma capacidade pública/gratuita. Use antes de dizer que não há ferramenta para dados externos.","parameters":{"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer"}},"required":["query"]}}},
            {"type":"function","function":{"name":"execute_capability","description":"Executa uma capacidade encontrada no Capability Hub. Use somente IDs retornados por search_capabilities e forneça os parâmetros solicitados.","parameters":{"type":"object","properties":{"capability_id":{"type":"string"},"params":{"type":"object"}},"required":["capability_id"]}}},
            {"type":"function","function":{"name":"capability_stats","description":"Mostra quantidade de capacidades, provedores e grupos disponíveis.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"discover_public_apis","description":"Pesquisa APIs públicas no diretório APIs.guru quando o Capability Hub ainda não possui a função necessária.","parameters":{"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer"}},"required":["query"]}}},
            {"type":"function","function":{"name":"resolve_capability","description":"Verifica se o Jarvis já possui uma competência executável para um objetivo e registra uma lacuna se faltar capacidade.","parameters":{"type":"object","properties":{"goal":{"type":"string"}},"required":["goal"]}}},
            {"type":"function","function":{"name":"acquire_capability","description":"Procura caminhos seguros para aprender uma capacidade ausente: compõe Skills com primitivas existentes, procura APIs públicas e documentação. Não instala silenciosamente.","parameters":{"type":"object","properties":{"goal":{"type":"string"},"source_url":{"type":"string"}},"required":["goal"]}}},
            {"type":"function","function":{"name":"import_openapi","description":"Importa operações GET públicas de uma especificação OpenAPI JSON HTTPS como novas capacidades. Requer confirmação do usuário.","parameters":{"type":"object","properties":{"spec_url":{"type":"string"},"prefix":{"type":"string"}},"required":["spec_url"]}}},
            {"type":"function","function":{"name":"search_web","description":"Pesquisa a web pública sem chave. Use para descobrir páginas/fontes antes de fetch_public_url.","parameters":{"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer"}},"required":["query"]}}},
            {"type":"function","function":{"name":"find_public_sources","description":"Encontra fontes públicas/abertas adequadas ao assunto, priorizando fontes oficiais e informando operações disponíveis.","parameters":{"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer"}},"required":["query"]}}},
            {"type":"function","function":{"name":"query_public_data","description":"Consulta uma fonte estruturada encontrada por find_public_sources. Use somente uma operação listada pela fonte.","parameters":{"type":"object","properties":{"source_id":{"type":"string"},"operation":{"type":"string"},"params":{"type":"object"}},"required":["source_id","operation"]}}},
            {"type":"function","function":{"name":"discover_public_interfaces","description":"Inspeciona um site público HTTPS procurando OpenAPI/Swagger, RSS/Atom e sitemap.","parameters":{"type":"object","properties":{"url":{"type":"string"}},"required":["url"]}}},
            {"type":"function","function":{"name":"institutional_service","description":"Usa um serviço cotidiano do SindPetshop-SP pela aba persistente interna do Jarvis quando disponível (site, Instagram, dashboard, agenda, Slack etc.). Operações de leitura preferem a sessão autenticada da própria aba.","parameters":{"type":"object","properties":{"operation":{"type":"string","enum":["resolve","open","list","inspect","click","fill","reload"]},"query":{"type":"string"},"text":{"type":"string"},"field":{"type":"string"},"selector":{"type":"string"},"value":{"type":"string"},"max_chars":{"type":"integer"}},"required":["operation"]}}},
            {"type":"function","function":{"name":"project_context","description":"Gerencia contexto persistente de projetos pessoais/de trabalho. Operações: list, create, select, current, add_note.","parameters":{"type":"object","properties":{"operation":{"type":"string","enum":["list","create","select","current","add_note"]},"name":{"type":"string"},"description":{"type":"string"},"project_id":{"type":"integer"},"title":{"type":"string"},"body":{"type":"string"}},"required":["operation"]}}},
            {"type":"function","function":{"name":"list_knowledge_collections","description":"Lista bases de conhecimento internas disponíveis para treinamento e respostas institucionais.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"search_knowledge","description":"Pesquisa informações em uma base de conhecimento local. Use para procedimentos internos, documentos e treinamento da equipe.","parameters":{"type":"object","properties":{"collection":{"type":"string"},"query":{"type":"string"},"limit":{"type":"integer"}},"required":["collection","query"]}}},
            {"type":"function","function":{"name":"institutional_context","description":"Lê contexto institucional compacto: perfil, glossário, políticas, regras editoriais e funções.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"institutional_evidence","description":"Pesquisa evidências citáveis em todas as bases institucionais. Use em regras, CCTs, procedimentos e treinamento.","parameters":{"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer"}},"required":["query"]}}},
            {"type":"function","function":{"name":"search_actions","description":"Pesquisa no Action Hub por ações locais: pesquisa, documentos, workspace, navegador, website/SEO, conteúdo, conhecimento, WordPress, automações, monitores, aprovações, integrações profissionais, equipe, notificações, diagnóstico e Observe & Learn. Use antes de tentar inventar uma ação especializada.","parameters":{"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer"}},"required":["query"]}}},
            {"type":"function","function":{"name":"execute_action","description":"Executa uma ação encontrada por search_actions. Use apenas IDs retornados pelo Action Hub e forneça os parâmetros pedidos.","parameters":{"type":"object","properties":{"action_id":{"type":"string"},"params":{"type":"object"}},"required":["action_id"]}}},
            {"type":"function","function":{"name":"action_stats","description":"Mostra quantidade de ações locais disponíveis por engine e grupo.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"search_workflows","description":"Pesquisa workflows compostos e reutilizáveis. Prefira um workflow quando uma tarefa exigir várias ações relacionadas.","parameters":{"type":"object","properties":{"query":{"type":"string"},"limit":{"type":"integer"}},"required":["query"]}}},
            {"type":"function","function":{"name":"execute_workflow","description":"Executa um workflow encontrado por search_workflows.","parameters":{"type":"object","properties":{"workflow_id":{"type":"string"},"params":{"type":"object"}},"required":["workflow_id"]}}},
            {"type":"function","function":{"name":"workflow_stats","description":"Mostra quantidade e grupos dos workflows disponíveis.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"create_long_job","description":"Cria um job persistente em segundo plano para objetivos que podem exigir muitas etapas, horas ou retomada após reinício. Não use para tarefas simples.","parameters":{"type":"object","properties":{"goal":{"type":"string"},"auto_resume":{"type":"boolean"},"priority":{"type":"integer"}},"required":["goal"]}}},
            {"type":"function","function":{"name":"list_long_jobs","description":"Lista jobs persistentes e seu progresso.","parameters":{"type":"object","properties":{"status":{"type":"string"},"limit":{"type":"integer"}}}}},
            {"type":"function","function":{"name":"long_job_status","description":"Obtém plano, progresso e estado de um job persistente.","parameters":{"type":"object","properties":{"job_id":{"type":"integer"}},"required":["job_id"]}}},
            {"type":"function","function":{"name":"set_task_plan","description":"Define um plano curto e visível para a tarefa autônoma atual. Use no início de tarefas com múltiplas etapas.","parameters":{"type":"object","properties":{"steps":{"type":"array","items":{"type":"string"}}},"required":["steps"]}}},
            {"type":"function","function":{"name":"get_world_state","description":"Lê estado atual resumido: navegador, janela desktop, base de conhecimento e modo de observação.","parameters":{"type":"object","properties":{}}}},
            {"type":"function","function":{"name":"suggest_learned_skills","description":"Analisa o histórico local e sugere sequências repetidas que podem virar Skills reutilizáveis.","parameters":{"type":"object","properties":{"min_repeats":{"type":"integer"}}}}},
            {"type":"function","function":{"name":"run_skill","description":"Executa uma skill salva. Skills parametrizadas aceitam inputs.","parameters":{"type":"object","properties":{"name":{"type":"string"},"inputs":{"type":"object"}},"required":["name"]}}},
        ]
        self.tool_schema_by_name = {
            item["function"]["name"]: item for item in self.tools_schema
        }

        if self.config.get("long_horizon_enabled", True):
            self.long_horizon.start_worker()

    def _tools_for_prompt(self, user_text):
        """Seleciona apenas ferramentas plausíveis; conversa comum não carrega schemas."""
        text = str(user_text or "").lower()
        names = set()
        complex_verbs = ("faça","faca","crie","prepare","analise","organize","compare","pesquise","procure","investigue","verifique","execute","altere","edite","resuma","encontre","automatize","agende","monitore")
        if any(k in text for k in complex_verbs): names.add("set_task_plan")
        if any(k in text for k in [
            "segundo plano","longo prazo","continue trabalhando","mesmo se demorar",
            "por horas","retome depois","checkpoint","job persistente"
        ]):
            names.update({"create_long_job","list_long_jobs","long_job_status"})
        if any(k in text for k in ["web","internet","fonte","dados públicos","dados publicos","estatística","estatistica","ibge","governo","câmara","camara","senado","cnj","datajud","cnpj","município","municipio","população","populacao","mercado de trabalho","emprego","pesquisa científica","pesquisa cientifica","api pública","api publica","banco central","selic","câmbio","cambio"]):
            names.update({"find_public_sources","query_public_data","search_web","fetch_public_url","discover_public_interfaces"})
        if any(k in text for k in ["url","site","página","pagina","link"]): names.update({"open_url","fetch_public_url","search_web"})
        if any(k in text for k in ["arquivo","pasta","workspace","salve","documento local"]):
            names.update({"search_actions","execute_action"})
            names.update({"create_file","read_file","list_files","open_folder"})
        if any(k in text for k in ["janela","clique","botão","botao","digite","pressione","menu","interface","desktop"]): names.update({"list_windows","select_window","inspect_selected_window","click_control","type_text","press_key"})
        if any(k in text for k in ["abra","aplicativo","programa"]): names.update({"open_app","open_url"})
        if any(k in text for k in ["clipboard","área de transferência","area de transferencia"]): names.update({"get_clipboard","set_clipboard"})
        if any(k in text for k in ["screenshot","captura","tela"]): names.add("take_screenshot")
        if any(k in text for k in ["sindpetshop","cct","convenção","convencao","procedimento interno","política interna","politica interna","treinamento","onboarding","base de conhecimento","documentos internos"]): names.update({"list_knowledge_collections","search_knowledge","institutional_evidence","institutional_context"})
        if any(k in text for k in ["instagram","facebook","linkedin","tiktok","slack","dashboard","insights","agenda sind","sindapp","site do sindicato","sistema interno"]):
            names.add("institutional_service")
        if any(k in text for k in ["projeto","campanha","contexto do projeto","nova campanha","retome o projeto","retomar projeto"]):
            names.add("project_context")
        if any(k in text for k in ["automação","automacao","agende","rotina","monitor","acompanhe","me avise","notifique","aprovação","aprovacao","integração","integracao","wordpress","portal","equipe","connector","workflow"]): names.update({"search_actions","execute_action","search_workflows","execute_workflow"})
        if any(k in text for k in ["skill","aprenda esta rotina","aprenda essa rotina"]): names.update({"run_skill","suggest_learned_skills"})
        if self.skills.relevant_skills(user_text, limit=3): names.add("run_skill")
        if hasattr(self, "apprenticeship") and self.apprenticeship.relevant(user_text, limit=2):
            names.update({"search_actions","execute_action","search_workflows","execute_workflow"})
        if any(k in text for k in ["api","openapi","swagger","capability","capacidade pública","capacidade publica"]): names.update({"search_capabilities","execute_capability","discover_public_apis","discover_public_interfaces"})
        if any(k in text for k in ["aprenda sozinho","descubra como","adquira capacidade","não sabe fazer","nao sabe fazer","não consigo fazer","nao consigo fazer","o que falta para","nova capacidade","nova competência","nova competencia"]):
            names.update({"resolve_capability","acquire_capability","search_actions","search_workflows","search_capabilities"})
        if not names and any(k in text for k in complex_verbs): names.update({"search_actions","execute_action","resolve_capability"})
        priority=["create_long_job","long_job_status","list_long_jobs","set_task_plan","resolve_capability","acquire_capability","find_public_sources","query_public_data","discover_public_interfaces","search_web","fetch_public_url","institutional_service","project_context","list_knowledge_collections","search_knowledge","institutional_evidence","institutional_context","search_actions","execute_action","search_workflows","execute_workflow","search_capabilities","execute_capability","discover_public_apis","open_url","open_app","create_file","read_file","list_files","open_folder","list_windows","select_window","inspect_selected_window","click_control","type_text","press_key","get_clipboard","set_clipboard","take_screenshot","run_skill","suggest_learned_skills"]
        ordered=[n for n in priority if n in names and n in self.tool_schema_by_name]
        return [self.tool_schema_by_name[n] for n in ordered[:10]]

    def _memory_context(self, user_text):
        items = self.memory.relevant(
            user_text,
            limit=self.config.get("memory_retrieval_limit", 6)
        )

        if not items:
            return ""

        lines = []
        for item in items:
            if item.get("kind") == "alias":
                lines.append(f"- Alias: {item['key']} = {item['value']}")
            else:
                lines.append(f"- {item['value']}")

        return "\nMemórias relevantes:\n" + "\n".join(lines)

    def system_prompt(self, user_text=""):
        mem = self._memory_context(user_text)
        public_stats = self.public_data.stats()
        service_stats = self.services.stats()
        long_stats = self.long_horizon.stats() if hasattr(self, "long_horizon") else {}
        conversation_stats = self.conversations.stats()
        lessons = self.learning.relevant(user_text, limit=4)
        reflections = self.reflections.relevant(user_text, limit=3)
        lesson_text = "\n".join(f"- {x.get('lesson')}" for x in lessons) if lessons else "- nenhuma"
        reflection_text = "\n".join(f"- {x.get('insight')}" for x in reflections) if reflections else "- nenhuma"
        project_context = self.projects.context(user_text, max_chars=1200).get("text","")
        procedure_context = self.apprenticeship.context(user_text, limit=2, max_chars=2200).get("text", "") if hasattr(self, "apprenticeship") else ""
        skill_context = self.skills.relevant_context(user_text, limit=3).get("text", "")
        acquisition_context = self.acquisition.context(user_text, max_chars=1800).get("text", "") if hasattr(self, "acquisition") else ""
        acquisition_stats = self.acquisition.stats() if hasattr(self, "acquisition") else {}
        swarm_stats = self.swarm.stats() if hasattr(self, "swarm") else {}
        return f"""Você é Jarvis, um GPT pessoal local.
Converse naturalmente em português e mantenha continuidade. Entenda o objetivo e decida sozinho se deve responder, pesquisar, consultar conhecimento ou agir.

PRINCÍPIOS
- Conversa comum não é comando.
- Actions, Workflows, APIs e automações são infraestrutura interna; não despeje catálogos sem pedido.
- Para tarefas complexas, planeje curto, execute, observe e tente alternativa segura.
- Nunca declare sucesso quando uma ferramenta falhou.
- Para fatos atuais/externos, prefira fontes oficiais/primárias e dados estruturados quando existirem.
- Para assuntos institucionais, procure evidência na Knowledge Base/CCTs; não invente lacunas.
- Para serviços cotidianos do SindPetshop-SP (Insights, Agenda, Facebook, LinkedIn, Instagram, TikTok, Sistema, Slack e Site), prefira a aba institucional persistente já presente no Jarvis. Use Google/navegador externo apenas como fallback quando a aba não servir ao objetivo.
- Sessões autenticadas dessas abas pertencem ao usuário; nunca peça ou armazene senha desnecessariamente.
- Use computador e integrações apenas quando ajudarem o objetivo.
- High/critical continuam sujeitos à governança.
- Nunca exponha senhas, tokens, chain-of-thought, análise passo a passo interna ou tags <think>.
- Entregue apenas conclusão, ações executadas, evidências úteis e progresso necessário.
- Jarvis Mobile é somente uma interface remota do Jarvis que roda no computador host.
- Se o usuário estiver no celular, não afirme que controla aplicativos do telefone; ações de desktop continuam acontecendo no computador host.
- Aprenda com preferências/correções explícitas e reutilize-as somente quando relevantes.
- Se faltar uma capacidade, não trate isso como impossibilidade definitiva: use resolve_capability/acquire_capability para procurar um caminho seguro antes de desistir.
- O Capability Acquisition Engine pode compor novas Skills apenas com primitivas já confiáveis, descobrir APIs públicas read-only e registrar lacunas; nunca invente que uma capacidade foi instalada.
- Se descoberta automática não encontrar executor confiável, peça ensino por explicação ou demonstração e reutilize o aprendizado depois.
- Quando houver um procedimento ensinado relevante, trate-o como instrução operacional do usuário, respeitando governança e confirmações.
- Em tarefas complexas, use o trabalho do Swarm/Blackboard como orientação; não exponha discussões internas dos agentes.

CONTEXTO
- Conversas persistentes: {conversation_stats.get('sessions',0)}; mensagens: {conversation_stats.get('messages',0)}.
- Fontes públicas catalogadas: {public_stats.get('sources',0)}; oficiais: {public_stats.get('official',0)}.
- Serviços cotidianos SindPetshop-SP mapeados: {service_stats.get('services',0)}.
- Swarm Intelligence: {swarm_stats.get('agents',0)} papéis; {swarm_stats.get('sessions',0)} coordenações registradas.
- Capability Acquisition: {sum(acquisition_stats.get('gaps',{}).values()) if acquisition_stats else 0} lacuna(s) registradas; {acquisition_stats.get('candidates',{}).get('installed',0) if acquisition_stats else 0} aquisição(ões) instalada(s).
- Long-Horizon: {long_stats.get('jobs',0)} job(s) persistentes; {long_stats.get('active',0)} ativo(s).
- Para objetivos extensos, use create_long_job em vez de abandonar a tarefa ao atingir um limite estrutural.
- Workspace: {self.workspace}
- Janela selecionada: {self.deep_access.snapshot().get('title') or 'nenhuma'}

LIÇÕES RELEVANTES
{lesson_text}

REFLEXÕES RELEVANTES
{reflection_text}

PROJETO ATUAL
{project_context or "- nenhum projeto ativo"}

PROCEDIMENTOS ENSINADOS RELEVANTES
{procedure_context or "- nenhum"}

SKILLS APRENDIDAS RELEVANTES
{skill_context or "- nenhuma"}

AQUISIÇÃO DE CAPACIDADE RELEVANTE
{acquisition_context or "- nenhuma lacuna/candidato relacionado"}
{mem}
"""

    def _resolve_path_args(self, name, args):
        args = dict(args)

        path_fields = {
            "create_folder": ["path"],
            "list_files": ["path"],
            "search_files": ["root"],
            "create_file": ["path"],
            "read_file": ["path"],
            "rename_item": ["path"],
            "copy_item": ["source", "destination"],
            "move_item": ["source", "destination"],
            "delete_item": ["path"],
            "open_folder": ["path"],
        }.get(name, [])

        for field in path_fields:
            if field in args:
                args[field] = self.memory.resolve_alias(args[field])

        return args

    def _run_memory_command(self, cmd):
        action = cmd["action"]

        if action == "alias":
            r = self.memory.set_alias(cmd["alias"], cmd["target"])
            return (
                f"Aprendido. Quando você disser “{r['alias']}”, "
                f"vou considerar “{r['target']}”."
            )

        if action == "remember":
            self.memory.remember(cmd["value"])
            return "Memória salva."

        if action == "forget":
            r = self.memory.forget(cmd["query"])
            total = r["deleted_memories"] + r["deleted_aliases"]
            return (
                f"Removi {total} item(ns) da memória local."
                if total
                else "Não encontrei memória correspondente."
            )

        if action == "list":
            memories = self.memory.list_memories(limit=50)
            aliases = self.memory.list_aliases()
            parts = []

            if aliases:
                parts.append(
                    "Aliases:\n" +
                    "\n".join(
                        f"• {a['alias']} → {a['target']}"
                        for a in aliases
                    )
                )

            if memories:
                parts.append(
                    "Memórias:\n" +
                    "\n".join(f"• {m['value']}" for m in memories)
                )

            return (
                "\n\n".join(parts)
                if parts
                else "Ainda não tenho memórias salvas."
            )

        if action == "recall":
            items = self.memory.relevant(cmd["query"], limit=10)
            if not items:
                return "Não encontrei nada relevante na memória."

            lines = []
            for item in items:
                if item.get("kind") == "alias":
                    lines.append(f"• {item['key']} → {item['value']}")
                else:
                    lines.append(f"• {item['value']}")

            return "Lembro disto:\n" + "\n".join(lines)

        return None

    def _run_skill_command(self, cmd, status=None, confirm_callback=None):
        action = cmd["action"]

        if action == "save_recent":
            count = max(
                1,
                min(
                    int(cmd["count"]),
                    int(self.config.get("max_skill_steps", 25))
                )
            )

            r = self.skills.save_from_recent_actions(
                name=cmd["name"],
                count=count,
            )

            if not r.get("ok"):
                return f"Não consegui salvar a skill: {r.get('error')}"

            return (
                f"Skill “{r['name']}” salva com {r['steps']} passo(s)."
            )

        if action == "error":
            return cmd.get("error", "Comando de skill inválido.")

        if action == "run":
            return self.run_skill(
                cmd["name"],
                inputs=cmd.get("inputs", {}),
                status=status,
                confirm_callback=confirm_callback,
            )

        if action == "delete":
            if confirm_callback:
                approved = confirm_callback(
                    "Excluir skill",
                    f"Excluir a skill “{cmd['name']}”?"
                )
                if not approved:
                    return "Ação cancelada."

            r = self.skills.delete_skill(cmd["name"])
            return (
                f"Skill “{r['name']}” excluída."
                if r.get("ok")
                else f"Não consegui excluir: {r.get('error')}"
            )

        if action == "list":
            items = self.skills.list_skills()

            if not items:
                return "Ainda não existem skills salvas."

            return "Skills:\n" + "\n".join(
                f"• {i['name']} — {i['steps']} passo(s)"
                for i in items
            )

        if action == "suggest_patterns":
            return self.summarize("suggest_learned_skills", self.pattern_miner.suggest(min_repeats=2))

        if action == "recent_actions":
            items = self.skills.recent_actions(cmd["count"])

            if not items:
                return "Ainda não há ações recentes registradas."

            lines = []
            for i, item in enumerate(items, 1):
                lines.append(
                    f"{i}. {item['tool']} {json.dumps(item.get('args', {}), ensure_ascii=False)}"
                )

            return "Ações recentes:\n" + "\n".join(lines)

        return None


    def _run_capability_command(self, cmd, status=None, confirm_callback=None):
        action = cmd.get("action")
        if action == "error":
            return cmd.get("error", "Comando de capacidade inválido.")
        if action == "stats":
            return self.summarize("capability_stats", self.capabilities.stats())
        if action == "providers":
            stats = self.capabilities.stats()
            providers = stats.get("providers", {})
            return "Provedores de capacidades:\n" + "\n".join(
                f"• {name}: {count}" for name, count in sorted(providers.items())
            )
        if action == "groups":
            stats = self.capabilities.stats()
            groups = stats.get("groups", {})
            return "Grupos de capacidades:\n" + "\n".join(
                f"• {name}: {count}" for name, count in sorted(groups.items())
            )
        if action == "list_filter":
            value = cmd.get("value", "")
            by_provider = self.capabilities.list(provider=value, limit=100)
            if by_provider.get("count", 0):
                items = by_provider.get("items", [])
            else:
                items = self.capabilities.list(group=value, limit=100).get("items", [])
            if not items:
                return self.summarize("search_capabilities", self.capabilities.search(value, limit=25))
            return "Capacidades:\n" + "\n".join(
                f"• {x.get('id')} — {x.get('description')}" for x in items[:100]
            )
        if action == "search":
            if status:
                status("Pesquisando capacidades")
            return self.summarize("search_capabilities", self.capabilities.search(cmd.get("query", ""), limit=15))
        if action == "discover":
            if status:
                status("Descobrindo APIs públicas")
            return self.summarize("discover_public_apis", self.capabilities.discover_public_apis(cmd.get("query", ""), limit=10))
        if action == "execute":
            if status:
                status(f"Executando capacidade: {cmd.get('id')}")
            result = self.capabilities.execute(cmd.get("id"), cmd.get("params", {}))
            return self.summarize("execute_capability", result)
        return None


    def _pending_approval_for_automation(self, job_id):
        try:
            items = self.approvals.pending(limit=500).get("items", [])
            return next((x for x in items if x.get("source_type")=="automation" and str(x.get("source_id"))==str(job_id)), None)
        except Exception:
            return None

    def _automation_needs_approval(self, job):
        """Retorna True quando a execução foi colocada na fila de aprovação."""
        risk = "read"
        requires = bool(job.get("require_confirmation"))
        target_type = str(job.get("target_type", "action")).lower()
        target_id = str(job.get("target_id", ""))

        if target_type == "action":
            meta = self.actions.get(target_id) or {}
            risk = meta.get("risk", "read")
            requires = requires or risk in {"high", "critical"}
        elif target_type == "workflow":
            meta = self.workflows.get(target_id) or {}
            risk = meta.get("risk", "read")
            requires = requires or risk in {"high", "critical"}
        elif target_type == "skill":
            # Skills podem encapsular passos de risco que o scheduler não consegue
            # inferir estaticamente com segurança. Execução autônoma exige aprovação.
            risk = "write"
            requires = True
        elif target_type == "capability":
            risk = "read"

        if not requires:
            return False
        if self._pending_approval_for_automation(job.get("id")):
            return True

        self.approvals.create(
            title=f"Automação: {job.get('name')}",
            description=f"Execução agendada de {target_type}:{target_id}",
            source_type="automation",
            source_id=str(job.get("id")),
            action_id=target_id,
            payload={"job_id": job.get("id"), "target_type": target_type, "params": job.get("params", {})},
            risk=risk,
            expires_minutes=1440,
        )
        self.notifications.add(
            "Aprovação necessária",
            f"A automação “{job.get('name')}” aguarda autorização.",
            category="approval", severity="warning", source="automation", source_id=str(job.get("id")),
        )
        return True

    def _execute_automation_job(self, job):
        target_type = str(job.get("target_type", "action")).lower()
        target_id = str(job.get("target_id", ""))
        params = dict(job.get("params") or {})

        if target_type == "action":
            return self.actions.execute(target_id, params)
        if target_type == "workflow":
            return self.workflows.execute(target_id, params=params)
        if target_type == "capability":
            return self.capabilities.execute(target_id, params)
        if target_type == "skill":
            message = self.run_skill(target_id, inputs=params, confirm_callback=None)
            failed = "interrompida" in str(message).lower() or "não consegui" in str(message).lower()
            return {"ok": not failed, "message": message, "error": message if failed else None}
        return {"ok": False, "error": f"target_type de automação desconhecido: {target_type}"}

    def _approval_resolution(self, item):
        source=str(item.get("source_type",""))
        status=str(item.get("status",""))
        if source=="automation" and status in {"rejected","cancelled","expired"}:
            payload=dict(item.get("payload") or {})
            job_id=payload.get("job_id") or item.get("source_id")
            if job_id:
                self.automations.reject_approval(int(job_id), reason=item.get("resolution_note") or f"Aprovação {status}.")
                self.notifications.add(
                    "Automação não autorizada",
                    f"A execução da automação #{job_id} foi {status}.",
                    category="approval",severity="info",source="automation",source_id=str(job_id),
                )
        return {"ok":True}

    def _execute_approved_item(self, item):
        source = str(item.get("source_type", ""))
        payload = dict(item.get("payload") or {})
        if source == "automation":
            job_id = payload.get("job_id") or item.get("source_id")
            return self.automations.run_now(int(job_id))
        if source == "action":
            return self.actions.execute(item.get("action_id", ""), payload.get("params", payload))
        if source == "workflow":
            return self.workflows.execute(item.get("action_id", ""), params=payload.get("params", payload))
        return {"ok": False, "error": f"Tipo de aprovação sem executor: {source}"}

    def _monitor_notification(self, monitor, result):
        self.notifications.add(
            f"Alteração detectada: {monitor.get('name')}",
            f"O monitor {monitor.get('monitor_type')} detectou uma mudança.",
            category="monitor", severity="info", source="monitor", source_id=str(monitor.get("id")),
            payload={"event_id": result.get("event_id"), "type": monitor.get("monitor_type")},
        )

    def _automation_notification(self, job, result):
        if result.get("ok"):
            if "notify" not in (job.get("tags") or []):
                return
            severity="success"; title=f"Automação concluída: {job.get('name')}"
            message="A execução agendada foi concluída."
        else:
            severity="error"; title=f"Falha na automação: {job.get('name')}"
            message=str(result.get("error", "Falha desconhecida."))[:800]
        self.notifications.add(title, message, category="automation", severity=severity,
                               source="automation", source_id=str(job.get("id")), payload=result)

    def _plan_long_horizon_job(self, job):
        """Planner pequeno e estruturado. Fallback do engine cobre falhas do modelo."""
        goal = str(job.get("goal") or "").strip()
        if not goal:
            return {"steps": []}

        prompt = f"""
OBJETIVO DE LONGO PRAZO:
{goal}

Crie um plano operacional de 3 a {int(self.config.get('long_horizon_max_steps',8))} etapas.
Cada etapa precisa conseguir ser executada e checkpointada separadamente.

Retorne SOMENTE JSON válido neste formato:
{{
  "steps": [
    {{
      "title": "nome curto",
      "instruction": "instrução autossuficiente da etapa",
      "retry_safe": true
    }}
  ]
}}

Regras:
- leitura, pesquisa, análise, comparação, elaboração de rascunho e verificação normalmente são retry_safe=true;
- publicar, enviar mensagem, excluir, mover, cadastrar, alterar sistema externo ou qualquer efeito não idempotente deve ser retry_safe=false;
- não inclua uma etapa genérica chamada apenas "planejar";
- a última etapa deve verificar o resultado.
""".strip()

        with self._execution_lock:
            response = self.models.chat(
                messages=[
                    {"role": "system", "content": "Você é o Planner interno do Jarvis. Gere somente o JSON solicitado, sem markdown."},
                    {"role": "user", "content": prompt},
                ],
                user_text=goal,
                force="fast",
            )

        content = str(((response.get("message") or {}).get("content") or "")).strip()
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.I | re.S).strip()
        match = re.search(r"\{[\s\S]*\}", content)
        if match:
            content = match.group(0)
        try:
            data = json.loads(content)
            steps = data.get("steps") if isinstance(data, dict) else None
            if isinstance(steps, list):
                return {"steps": steps[:int(self.config.get("long_horizon_max_steps", 8))]}
        except Exception:
            pass
        return {"steps": []}

    def _execute_long_horizon_step(self, job, step):
        """
        Executa uma única etapa e devolve o controle ao scheduler.
        Isso cria um checkpoint natural entre cada uso pesado do modelo.
        """
        previous = []
        for item in job.get("steps", []):
            if item.get("status") == "completed" and item.get("result_text"):
                previous.append(
                    f"Etapa {int(item.get('position',0))+1} — {item.get('title')}:\n"
                    f"{str(item.get('result_text'))[:1800]}"
                )
        previous_text = "\n\n".join(previous[-3:])[:5000]

        prompt = f"""
JOB PERSISTENTE #{job.get('id')}
OBJETIVO GERAL:
{job.get('goal')}

ETAPA ATUAL:
{step.get('title')}

INSTRUÇÃO:
{step.get('instruction')}

CHECKPOINTS ANTERIORES:
{previous_text or 'Nenhum checkpoint anterior necessário.'}

Execute SOMENTE esta etapa. Use ferramentas reais quando necessário.
Não declare sucesso se não houver evidência suficiente.
Se precisar de login, aprovação, dado do usuário ou confirmação para um efeito externo,
explique explicitamente o que está aguardando.
Entregue uma conclusão curta desta etapa para ser armazenada no checkpoint.
""".strip()

        with self._execution_lock:
            try:
                output = self._run_internal(
                    prompt,
                    status=lambda detail: self.long_horizon._event(
                        job.get("id"), "progress", str(detail), {"step": step.get("position")}
                    ),
                    confirm_callback=None,
                )
            except Exception as exc:
                return {"ok": False, "error": str(exc)}

        output = str(output or "").strip()
        low = output.lower()
        failure_markers = (
            "não consegui", "nao consegui", "falha", "erro:", "não foi possível",
            "nao foi possivel", "requer confirmação", "requer confirmacao",
            "aguarda autorização", "aguarda autorizacao", "preciso que você",
            "preciso que voce", "faça login", "faca login",
        )
        if any(x in low for x in failure_markers):
            return {"ok": False, "error": output, "output": output}
        return {"ok": True, "output": output}

    def _long_horizon_notification(self, job, result):
        status = str(result.get("status") or job.get("status") or "")
        if status == "completed":
            title = f"Job concluído: {job.get('goal','')[:70]}"
            message = "A tarefa de longo prazo terminou. Abra Atividade para ver os checkpoints."
            severity = "success"
        elif status == "waiting_user":
            title = f"Job aguardando você: {job.get('goal','')[:70]}"
            message = str(result.get("error") or job.get("last_error") or "Intervenção necessária.")[:800]
            severity = "warning"
        else:
            title = f"Falha em job: {job.get('goal','')[:70]}"
            message = str(result.get("error") or job.get("last_error") or "Falha desconhecida.")[:800]
            severity = "error"
        try:
            self.notifications.add(
                title, message, category="long_horizon", severity=severity,
                source="long_horizon", source_id=str(job.get("id")),
                payload={"job_id": job.get("id"), "status": status}
            )
        except Exception:
            pass

    def _run_long_horizon_command(self, cmd, status=None, confirm_callback=None):
        action = cmd.get("action")
        if action == "create":
            if status:
                status("Criando tarefa persistente de longo prazo")
            result = self.long_horizon.create(
                cmd.get("goal", ""),
                project_id=self.projects.current_id(),
                session_id=self.conversations.current_session_id,
                auto_resume=bool(cmd.get("auto_resume", True)),
                priority=60,
                metadata={"created_from": "conversation"},
            )
            if not result.get("ok"):
                return f"Não consegui criar o job: {result.get('error')}"
            job = result["data"]
            return (
                f"Criei o Job persistente #{job.get('id')}: {job.get('goal')}\n\n"
                "Ele será planejado e executado em checkpoints. "
                "Se o Jarvis for reiniciado, etapas seguras podem ser retomadas automaticamente."
            )

        if action == "list":
            result = self.long_horizon.list(limit=30)
            items = result.get("items", [])
            if not items:
                return "Ainda não há jobs de longo prazo."
            lines = []
            for x in items:
                progress = x.get("progress", {})
                lines.append(
                    f"• #{x.get('id')} [{x.get('status')}] {progress.get('percent',0)}% — {x.get('goal')}"
                )
            return "Jobs persistentes:\n" + "\n".join(lines)

        if action == "stats":
            stats = self.long_horizon.stats()
            return (
                f"Long-Horizon: {stats.get('jobs',0)} jobs registrados; "
                f"{stats.get('active',0)} ativos.\nEstados: {stats.get('statuses',{})}"
            )

        job_id = int(cmd.get("job_id") or 0)
        if action == "get":
            result = self.long_horizon.get(job_id)
            if not result.get("ok"):
                return result.get("error")
            job = result["data"]
            lines = [
                f"Job #{job_id} — {job.get('status')}",
                f"Objetivo: {job.get('goal')}",
                f"Progresso: {job.get('progress',{}).get('percent',0)}%",
            ]
            for step in job.get("steps", []):
                marker = "✓" if step.get("status") == "completed" else "●" if step.get("status") == "running" else "○"
                lines.append(f"{marker} {int(step.get('position',0))+1}. {step.get('title')} [{step.get('status')}]")
            if job.get("last_error"):
                lines.append(f"Observação: {job.get('last_error')}")
            return "\n".join(lines)

        if action == "pause":
            result = self.long_horizon.pause(job_id)
        elif action == "resume":
            if cmd.get("force") and confirm_callback:
                if not confirm_callback(
                    "Forçar retomada",
                    "A etapa anterior pode ter causado um efeito externo antes da interrupção. Reexecutar mesmo assim?"
                ):
                    return "Retomada forçada cancelada."
            result = self.long_horizon.resume(job_id, force=bool(cmd.get("force")))
        elif action == "cancel":
            result = self.long_horizon.cancel(job_id)
        else:
            return "Comando de Long-Horizon desconhecido."

        if result.get("ok"):
            return f"Job #{job_id}: {result.get('status','atualizado')}."
        return result.get("error") or "Não consegui atualizar o job."

    def shutdown(self):
        try:self.long_horizon.stop_worker()
        except Exception:pass
        try:self.automations.stop_worker()
        except Exception:pass
        try:self.browser_agent.stop()
        except Exception:pass
        return {"ok": True}

    def _run_action_command(self, cmd, status=None, confirm_callback=None):
        action = cmd.get("action")

        if action == "error":
            return cmd.get("error", "Comando de ação inválido.")

        if action == "stats":
            return self.summarize("action_stats", self.actions.stats())

        if action == "search":
            if status:
                status("Pesquisando ações locais")
            return self.summarize(
                "search_actions",
                self.actions.search(cmd.get("query", ""), limit=20),
            )

        if action == "execute":
            if status:
                status(f"Executando ação: {cmd.get('id')}")
            result = self._execute_action_with_permission(
                cmd.get("id", ""),
                cmd.get("params", {}),
                confirm_callback=confirm_callback,
            )
            return self.summarize("execute_action", result)

        return None

    def _execute_action_with_permission(self, action_id, params, confirm_callback=None):
        meta = self.actions.get(action_id)
        if not meta:
            return {"ok": False, "error": f"Ação não encontrada: {action_id}"}

        risk = meta.get("risk", "read")

        if risk in {"high", "critical"}:
            if not confirm_callback or not confirm_callback(
                "Confirmar ação externa",
                f"Jarvis quer executar:\\n{action_id}\\n\\n{meta.get('description','')}\\n\\nDeseja continuar?"
            ):
                return {"ok": False, "error": "Ação cancelada pelo usuário.", "action": action_id}

        if action_id == "observe.candidate.approve":
            session_id = str((params or {}).get("session_id", "")).strip()
            candidate_path = self.observe.candidates_dir / f"{session_id}.json"
            if not candidate_path.exists():
                return {"ok": False, "error": "Candidato observado não encontrado.", "action": action_id}
            try:
                candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
                name = str((params or {}).get("name") or candidate.get("name") or f"observed_{session_id}")
                saved = self.skills.save_parametric_skill(
                    name=name,
                    steps=candidate.get("steps", []),
                    inputs=candidate.get("inputs", {}),
                    description=f"Aprendida por demonstração na sessão {session_id}.",
                )
                return {
                    "ok": bool(saved.get("ok")),
                    "action": action_id,
                    "engine": "observe",
                    "skill": name,
                    "steps": saved.get("steps"),
                    "inputs": list((candidate.get("inputs") or {}).keys()),
                    "error": saved.get("error"),
                }
            except Exception as exc:
                return {"ok": False, "error": str(exc), "action": action_id}

        result = self.actions.execute(action_id, params or {})

        # Registra ação sem guardar conteúdo potencialmente sensível de inputs.
        safe_args = dict(params or {})
        sensitive_keys = {
            "password", "senha", "token", "secret", "client_secret",
            "api_key", "apikey", "authorization", "credential"
        }
        mask_value_for_actions = {
            "connector.secret_set",
        }
        for key in list(safe_args):
            low = str(key).lower()
            should_mask = (
                low in sensitive_keys
                or any(part in low for part in ("password", "senha", "token", "secret", "api_key", "apikey"))
                or (
                    action_id in mask_value_for_actions
                    and low == "value"
                )
                or (
                    (action_id.startswith("browser.fill") or action_id.startswith("browser.type"))
                    and low in {"value", "text"}
                )
            )
            if should_mask and safe_args.get(key) is not None:
                safe_args[key] = f"<masked:{len(str(safe_args[key]))}>"

        try:
            self.skills.log_action(
                "execute_action",
                {"action_id": action_id, "params": safe_args},
                result,
                source="action_hub",
            )
        except Exception:
            pass

        try:
            self.governance.audit(
                action_id,
                connector=meta.get("engine", ""),
                risk=risk,
                approved=True if risk in {"high", "critical"} else None,
                success=bool(result.get("ok")),
                detail={"params": safe_args, "error": result.get("error")},
            )
        except Exception:
            pass

        return result

    def _run_access_command(self, cmd, status=None, confirm_callback=None):
        action = cmd["action"]

        if action == "select_window":
            if status:
                status("Selecionando janela")
            r = self.deep_access.select_window(cmd["query"])
            return (
                f"Janela selecionada: {r.get('title')}"
                if r.get("ok")
                else f"Não consegui selecionar a janela: {r.get('error')}"
            )

        if action == "selected_window":
            snap = self.deep_access.snapshot()
            return (
                f"Janela selecionada: {snap.get('title')}"
                if snap.get("selected")
                else "Nenhuma janela está selecionada."
            )

        if action == "inspect_window":
            if status:
                status("Observando interface")
            r = self.deep_access.inspect_selected(
                max_controls=self.config.get("deep_access", {}).get("max_controls", 90)
            )
            return self.summarize("inspect_selected_window", r)

        if action == "click_control":
            name = cmd["name"]
            if (
                self.config.get("deep_access", {}).get("confirm_risky_controls", True)
                and self.deep_access.is_risky_control(name)
            ):
                if not confirm_callback or not confirm_callback(
                    "Confirmar ação na interface",
                    f"Jarvis quer acionar o controle:\\n{name}\\n\\nDeseja continuar?"
                ):
                    return "Ação cancelada."

            if status:
                status(f"Acionando controle: {name}")

            r = self.deep_access.click_control(name)
            self._log_deep_action("click_control", {"name": name}, r)
            return self.summarize("click_control", r)

        if action == "type_text":
            if status:
                status("Digitando na janela selecionada")
            r = self.deep_access.type_text(cmd["text"])
            self._log_deep_action("type_text", {"chars": len(cmd["text"])}, r)
            return self.summarize("type_text", r)

        if action == "press_key":
            if status:
                status(f"Pressionando tecla: {cmd['key']}")
            r = self.deep_access.press_key(cmd["key"])
            self._log_deep_action("press_key", {"key": cmd["key"]}, r)
            return self.summarize("press_key", r)

        return None

    def _log_deep_action(self, tool, args, result):
        try:
            self.skills.log_action(tool, args, result, source="deep_access")
        except Exception:
            pass

    def run_skill(self, name, inputs=None, status=None, confirm_callback=None):
        skill = self.skills.get_skill(name)

        if not skill:
            return f"Skill “{name}” não encontrada."

        rendered = self.skills.render_skill(skill, inputs or {})
        if not rendered.get("ok"):
            return f"Não consegui iniciar a skill: {rendered.get('error')}"

        steps = rendered.get("steps", [])
        max_steps = int(self.config.get("max_skill_steps", 25))

        if not steps:
            return f"A skill “{skill['name']}” não possui passos."

        if len(steps) > max_steps:
            return (
                f"A skill possui {len(steps)} passos e excede o limite "
                f"de {max_steps}."
            )

        results = []
        self._executing_skill = True

        try:
            for index, step in enumerate(steps, 1):
                tool = step.get("tool")
                args = step.get("args", {})

                if status:
                    status(f"Skill {skill['name']}: passo {index}/{len(steps)}")

                result = self.dispatch(
                    tool,
                    args,
                    confirm_callback=confirm_callback,
                    log_action=True,
                    source=f"skill:{skill['name']}",
                )

                results.append((tool, result))

                if not result.get("ok"):
                    return (
                        f"Skill “{skill['name']}” interrompida no passo "
                        f"{index}: {result.get('error', 'erro desconhecido')}"
                    )
        finally:
            self._executing_skill = False

        return (
            f"Skill “{skill['name']}” concluída com "
            f"{len(results)} passo(s)."
        )

    def dispatch(
        self,
        name,
        args,
        confirm_callback=None,
        log_action=True,
        source="user",
    ):
        args = self._resolve_path_args(name, args)

        if name == "fetch_public_url":
            return fetch_public_url(args.get("url", ""))

        if name == "read_rss":
            return read_rss(args.get("url", ""), limit=args.get("limit", 20))

        if name == "search_web":
            return self.web_search.search(args.get("query", ""), limit=args.get("limit", 8))

        if name == "find_public_sources":
            return self.public_data.recommend(args.get("query", ""), limit=args.get("limit", 8))

        if name == "query_public_data":
            return self.public_data.query(args.get("source_id", ""), args.get("operation", ""), args.get("params", {}))

        if name == "discover_public_interfaces":
            return self.public_data.discover_interfaces(args.get("url", ""), save=True)

        if name == "institutional_service":
            operation = args.get("operation", "resolve")
            query = args.get("query", "")
            if operation == "list":
                return self.services.list(daily=True)
            if operation == "open":
                return self.services.open(query)
            if operation == "inspect":
                return self.services.tab_action(
                    query, "inspect", max_chars=int(args.get("max_chars", 14000))
                )
            if operation == "reload":
                return self.services.tab_action(query, "reload")
            if operation == "fill":
                return self.services.tab_action(
                    query, "fill",
                    field=args.get("field",""),
                    selector=args.get("selector",""),
                    value=args.get("value",""),
                )
            if operation == "click":
                click_text = str(args.get("text",""))
                risky = any(k in click_text.lower() for k in (
                    "publicar","postar","enviar","excluir","apagar","salvar",
                    "confirmar","aprovar","rejeitar","cadastrar","comprar","pagar"
                ))
                if risky and confirm_callback:
                    approved = confirm_callback(
                        "Confirmar ação na aba institucional",
                        f"O Jarvis pretende clicar em “{click_text}” dentro de {query}. Continuar?"
                    )
                    if not approved:
                        return {"ok": False, "cancelled": True, "error": "Ação cancelada pelo usuário."}
                return self.services.tab_action(query, "click", text=click_text)
            return self.services.resolve(query)

        if name == "project_context":
            operation = args.get("operation", "current")
            if operation == "list":
                return self.projects.list(status="active", limit=50)
            if operation == "create":
                result = self.projects.create(args.get("name",""), args.get("description",""))
                if result.get("ok"):
                    try:
                        self.projects.link_session(result["data"]["id"], self.conversations.current_session_id)
                    except Exception:
                        pass
                return result
            if operation == "select":
                pid = int(args.get("project_id") or 0)
                result = self.projects.set_current(pid or None)
                if pid:
                    try:self.projects.link_session(pid, self.conversations.current_session_id)
                    except Exception:pass
                return result
            if operation == "add_note":
                pid = int(args.get("project_id") or self.projects.current_id() or 0)
                if not pid:
                    return {"ok": False, "error": "Nenhum projeto ativo."}
                return self.projects.add_note(pid, args.get("title","Nota"), args.get("body",""))
            return self.projects.current()

        if name == "list_knowledge_collections":
            return self.knowledge.list_collections()

        if name == "search_knowledge":
            return self.knowledge.search(
                args.get("collection", ""),
                args.get("query", ""),
                limit=args.get("limit", 8),
            )

        if name == "institutional_context":
            return self.institutional.execute("context_bundle")

        if name == "institutional_evidence":
            return self.institutional_knowledge.execute(
                "evidence_pack", query=args.get("query", ""), limit=args.get("limit", 10)
            )

        if name == "create_long_job":
            return self.long_horizon.create(
                args.get("goal",""),
                project_id=self.projects.current_id(),
                session_id=self.conversations.current_session_id,
                auto_resume=bool(args.get("auto_resume", True)),
                priority=int(args.get("priority", 50)),
                metadata={"source": source or "agent_runtime"},
            )

        if name == "list_long_jobs":
            return self.long_horizon.list(
                status=args.get("status") or None,
                limit=int(args.get("limit", 20)),
            )

        if name == "long_job_status":
            return self.long_horizon.get(int(args.get("job_id") or 0))

        if name == "set_task_plan":
            if not self._active_task_id:
                return {"ok": False, "error": "Não há tarefa autônoma ativa."}
            return self.tasks.set_plan(self._active_task_id, args.get("steps", []))

        if name == "get_world_state":
            return {"ok": True, "state": world_snapshot(self)}

        if name == "search_workflows":
            return self.workflows.search(args.get("query", ""), limit=args.get("limit", 15))

        if name == "workflow_stats":
            return self.workflows.stats()

        if name == "execute_workflow":
            workflow_id = args.get("workflow_id", "")
            meta = self.workflows.get(workflow_id)
            if not meta:
                return {"ok": False, "error": f"Workflow não encontrado: {workflow_id}"}
            if meta.get("risk") in {"high", "critical"}:
                if not confirm_callback or not confirm_callback(
                    "Confirmar workflow",
                    f"Jarvis quer executar o workflow:\n{workflow_id}\n\n{meta.get('description','')}"
                ):
                    return {"ok": False, "error": "Workflow cancelado pelo usuário."}
            return self.workflows.execute(workflow_id, args.get("params", {}))

        if name == "search_actions":
            return self.actions.search(args.get("query", ""), limit=args.get("limit", 15))

        if name == "action_stats":
            return self.actions.stats()

        if name == "execute_action":
            return self._execute_action_with_permission(
                args.get("action_id", ""),
                args.get("params", {}),
                confirm_callback=confirm_callback,
            )

        if name == "resolve_capability":
            return self.acquisition.resolve(args.get("goal", ""), create_gap=True)

        if name == "acquire_capability":
            return self.acquisition.discover(
                args.get("goal", ""),
                source_url=args.get("source_url"),
                status=None,
            )

        if name == "search_capabilities":
            return self.capabilities.search(args.get("query", ""), limit=args.get("limit", 12))

        if name == "execute_capability":
            return self.capabilities.execute(args.get("capability_id", ""), args.get("params", {}))

        if name == "capability_stats":
            return self.capabilities.stats()

        if name == "discover_public_apis":
            return self.capabilities.discover_public_apis(args.get("query", ""), limit=args.get("limit", 8))

        if name == "import_openapi":
            if not confirm_callback or not confirm_callback(
                "Adicionar novas capacidades",
                f"Importar operações GET públicas desta especificação OpenAPI?\n\n{args.get('spec_url','')}"
            ):
                return {"ok": False, "error": "Importação cancelada pelo usuário."}
            return self.capabilities.import_openapi(
                args.get("spec_url", ""),
                prefix=args.get("prefix", "imported")
            )

        if name == "select_window":
            result = self.deep_access.select_window(args.get("query", ""))
            self._log_deep_action(name, {"query": args.get("query", "")}, result)
            return result

        if name == "inspect_selected_window":
            return self.deep_access.inspect_selected(
                max_controls=self.config.get("deep_access", {}).get("max_controls", 90)
            )

        if name == "click_control":
            control_name = args.get("name", "")
            if (
                self.config.get("deep_access", {}).get("confirm_risky_controls", True)
                and self.deep_access.is_risky_control(control_name)
            ):
                if not confirm_callback or not confirm_callback(
                    "Confirmar ação na interface",
                    f"Jarvis quer acionar o controle:\\n{control_name}\\n\\nDeseja continuar?"
                ):
                    return {"ok": False, "error": "Ação cancelada pelo usuário."}

            result = self.deep_access.click_control(
                control_name, args.get("control_type")
            )
            self._log_deep_action(
                name,
                {"name": control_name, "control_type": args.get("control_type")},
                result,
            )
            return result

        if name == "type_text":
            result = self.deep_access.type_text(
                text=args.get("text", ""),
                control_name=args.get("control_name"),
                clear_first=bool(args.get("clear_first", False)),
            )
            self._log_deep_action(
                name,
                {
                    "chars": len(str(args.get("text", ""))),
                    "control_name": args.get("control_name"),
                },
                result,
            )
            return result

        if name == "press_key":
            result = self.deep_access.press_key(args.get("key", ""))
            self._log_deep_action(name, {"key": args.get("key", "")}, result)
            return result

        if name == "suggest_learned_skills":
            return self.pattern_miner.suggest(min_repeats=args.get("min_repeats", 2))

        if name == "run_skill":
            result_text = self.run_skill(
                args.get("name", ""),
                inputs=args.get("inputs", {}),
                confirm_callback=confirm_callback,
            )
            return {"ok": True, "message": result_text}

        if name == "delete_item":
            if not confirm_callback or not confirm_callback(
                "Confirmar exclusão",
                f"Excluir:\n{args.get('path')}"
            ):
                result = {
                    "ok": False,
                    "error": "Ação cancelada pelo usuário."
                }
                if log_action:
                    self.skills.log_action(name, args, result, source=source)
                return result

        if name in {"copy_item", "move_item"}:
            d = self.files.normalize(args["destination"])
            if d.exists():
                if not confirm_callback or not confirm_callback(
                    "Confirmar sobrescrita",
                    f"O destino já existe:\n{d}\n\nDeseja substituir?"
                ):
                    result = {
                        "ok": False,
                        "error": "Ação cancelada pelo usuário."
                    }
                    if log_action:
                        self.skills.log_action(
                            name, args, result, source=source
                        )
                    return result

                args = dict(args)
                args["overwrite"] = True

        if name == "rename_item":
            src = self.files.normalize(args["path"])
            d = src.with_name(args["new_name"])

            if d.exists():
                if not confirm_callback or not confirm_callback(
                    "Confirmar substituição",
                    f"Já existe:\n{d}\n\nDeseja substituir?"
                ):
                    result = {
                        "ok": False,
                        "error": "Ação cancelada pelo usuário."
                    }
                    if log_action:
                        self.skills.log_action(
                            name, args, result, source=source
                        )
                    return result

                args = dict(args)
                args["overwrite"] = True

        mapping = {
            "create_folder": self.files.create_folder,
            "list_files": self.files.list_files,
            "search_files": lambda **kw: self.files.search_files(
                max_results=self.config.get("max_search_results", 100),
                **kw
            ),
            "create_file": self.files.create_file,
            "read_file": self.files.read_file,
            "rename_item": self.files.rename_item,
            "copy_item": self.files.copy_item,
            "move_item": self.files.move_item,
            "delete_item": self.files.delete_item,
            "open_folder": open_folder,
            "open_app": open_app,
            "open_url": open_url,
            "get_clipboard": lambda: get_clipboard_text(),
            "set_clipboard": set_clipboard_text,
            "take_screenshot": lambda: take_screenshot(self.screenshot_dir),
            "list_windows": lambda: list_windows(),
            "list_processes": lambda: list_processes(),
        }

        if name not in mapping:
            return {
                "ok": False,
                "error": f"Ferramenta desconhecida: {name}"
            }

        try:
            result = mapping[name](**args)
        except Exception as exc:
            result = {"ok": False, "error": str(exc)}

        if log_action:
            self.skills.log_action(
                name,
                args,
                result,
                source=source,
            )

        return result

    def summarize(self, name, r):
        if name == "run_skill":
            return r.get("message", "Skill executada.")

        if not r.get("ok"):
            return f"Não consegui concluir: {r.get('error','erro desconhecido')}"

        if name=="create_folder": return f"Pasta criada: {r.get('path')}"
        if name=="create_file": return f"Arquivo criado: {r.get('path')}"
        if name=="read_file": return f"Conteúdo:\n{r.get('content','')}"
        if name=="list_files":
            items=r.get("items",[])
            return "Itens:\n" + "\n".join(
                ("📁 " if i["type"]=="folder" else "📄 ")+i["name"]
                for i in items[:60]
            ) if items else "A pasta está vazia."
        if name=="search_files":
            items=r.get("results",[])
            return "Resultados:\n" + "\n".join(
                i["path"] for i in items[:60]
            ) if items else "Nenhum resultado."
        if name=="rename_item": return f"Renomeado para: {r.get('new_path')}"
        if name=="copy_item": return f"Copiado para: {r.get('destination')}"
        if name=="move_item": return f"Movido para: {r.get('destination')}"
        if name=="delete_item": return f"Excluído: {r.get('path')}"
        if name=="open_folder": return f"Pasta aberta: {r.get('path')}"
        if name=="open_app": return f"Aplicativo aberto: {r.get('app')}"
        if name=="open_url": return f"URL aberta: {r.get('url')}"
        if name=="get_clipboard": return f"Clipboard:\n{r.get('text','')}"
        if name=="set_clipboard": return "Texto copiado para o clipboard."
        if name=="take_screenshot": return f"Captura salva em: {r.get('path')}"
        if name=="list_windows":
            return "Janelas abertas:\n" + "\n".join(
                "• "+x for x in r.get("windows",[])[:50]
            )
        if name=="list_processes":
            return "Processos:\n" + "\n".join(
                f"• {p['name']} (PID {p['pid']})"
                for p in r.get("processes",[])[:60]
            )
        if name=="select_window":
            return f"Janela selecionada: {r.get('title')}"
        if name=="inspect_selected_window":
            controls = r.get("controls", [])
            if not controls:
                return "Nenhum controle acessível foi encontrado."
            lines = []
            for c in controls[:60]:
                label = c.get("name") or c.get("automation_id") or "(sem nome)"
                ctype = c.get("control_type") or "Control"
                lines.append(f"• [{ctype}] {label}")
            return f"Controles encontrados em {r.get('window')}:\n" + "\n".join(lines)
        if name=="click_control":
            return f"Controle acionado: {r.get('name')} ({r.get('control_type') or 'controle'})"
        if name=="type_text":
            return f"Texto digitado na janela selecionada ({r.get('chars', 0)} caractere(s))."
        if name=="press_key":
            return f"Tecla pressionada: {r.get('key')}"
        if name=="fetch_public_url":
            text = r.get("text", "")
            return f"Conteúdo de {r.get('url')}:\n{text[:9000]}"
        if name=="read_rss":
            items = r.get("items", [])
            if not items:
                return "Feed lido, mas nenhum item foi encontrado."
            return "Itens do feed:\n" + "\n".join(
                f"• {i.get('title')} — {i.get('published')} — {i.get('link')}" for i in items[:20]
            )
        if name=="search_web":
            items = r.get("items", [])
            if not items:
                attempts = r.get("attempts", [])
                detail = "; ".join(
                    f"{a.get('provider')}: {a.get('count',0)}" for a in attempts
                )
                return "A busca web não retornou resultados." + (f" Provedores tentados: {detail}." if detail else "")
            return f"Resultados da web via {r.get('provider','provedor público')}:\n" + "\n".join(
                f"• {i.get('title')} — {i.get('url')}\n  {i.get('snippet','')[:240]}"
                for i in items[:10]
            )
        if name=="institutional_context":
            profile=r.get("profile",{}); policies=r.get("policies",[]); glossary=r.get("glossary",[]); styles=r.get("style_rules",[])
            return (f"Contexto institucional: {len(profile)} campo(s) de perfil, {len(policies)} política(s), "
                    f"{len(glossary)} termo(s) e {len(styles)} regra(s) editorial(is).")
        if name=="institutional_evidence":
            items=r.get("items",[])
            if not items:return "A base institucional ainda não contém evidências para essa pergunta."
            return "Evidências institucionais:\n" + "\n".join(
                f"• {x.get('citation')} {x.get('title')} — {x.get('text','')[:700]}" for x in items[:10]
            )

        if name=="list_knowledge_collections":
            items = r.get("items", [])
            if not items:
                return "Nenhuma base de conhecimento foi criada ainda."
            return "Bases de conhecimento:\n" + "\n".join(
                f"• {i.get('collection')} — {i.get('docs')} documento(s)" for i in items
            )
        if name=="search_knowledge":
            items = r.get("items", [])
            if not items:
                return "Nenhum trecho relevante foi encontrado na base de conhecimento."
            return "Trechos da base de conhecimento:\n" + "\n".join(
                f"• {i.get('title')} — {i.get('source')}\n  {i.get('text','')[:800]}"
                for i in items[:8]
            )
        if name=="find_public_sources":
            items=r.get("items",[])
            if not items:return "Não encontrei uma fonte pública catalogada adequada."
            return "Fontes públicas adequadas:\n"+"\n".join(f"• {x.get('name')} ({x.get('id')}) — {x.get('access')} — operações: {', '.join(x.get('operations') or ['descoberta'])}" for x in items[:8])
        if name=="query_public_data":
            raw=json.dumps({k:v for k,v in r.items() if k not in {'html'}},ensure_ascii=False,default=str)
            return ("Consulta pública concluída:\n"+raw[:9000]) if r.get("ok") else f"Consulta pública falhou: {r.get('error')}"
        if name=="discover_public_interfaces":
            if not r.get("ok"):return f"Não consegui inspecionar interfaces públicas: {r.get('error')}"
            items=r.get("interfaces",[])
            return "Interfaces detectadas:\n"+"\n".join(f"• {x.get('kind')}: {x.get('url')}" for x in items[:20]) if items else "Nenhuma interface estruturada óbvia foi detectada."

        if name=="capability_stats":
            providers = r.get("providers", {})
            groups = r.get("groups", {})
            return (
                f"Capability Hub: {r.get('capabilities',0)} capacidades em "
                f"{len(providers)} provedores e {len(groups)} grupos."
            )
        if name=="resolve_capability":
            if r.get("status") == "existing":
                return f"Já encontrei um caminho existente: {r.get('kind')} `{r.get('id')}` (confiança {r.get('score',0):.2f})."
            return f"Registrei uma lacuna de capacidade #{r.get('gap_id')}: {r.get('goal')}. Posso tentar descobrir/compor uma nova competência."
        if name=="acquire_capability":
            if r.get("status") == "existing":
                return self.summarize("resolve_capability", r)
            items = r.get("candidates", [])
            if not items:
                return (
                    f"Não encontrei um executor confiável para `{r.get('goal')}`. Registrei a lacuna #{r.get('gap_id')}. "
                    "Posso aprender por explicação (`Quero te ensinar como ...`) ou demonstração (`Observe enquanto eu faço ...`)."
                )
            lines=[]
            for item in items[:8]:
                lines.append(f"• #{item.get('id')} [{item.get('kind')}] {item.get('title')} — risco {item.get('risk')} — estado {item.get('status')}")
            return (
                f"Capability Acquisition encontrou {len(items)} caminho(s) para `{r.get('goal')}` (lacuna #{r.get('gap_id')}):\n" +
                "\n".join(lines) +
                "\n\nVocê pode pedir `teste o candidato #N` e depois `instale a capacidade #N`."
            )
        if name=="list_capability_gaps":
            items=r.get("items",[])
            if not items:return "Não há lacunas de capacidade registradas."
            return "Lacunas de capacidade:\n"+"\n".join(f"• #{x.get('id')} [{x.get('status')}] {x.get('goal')}" for x in items[:30])
        if name=="list_capability_candidates":
            items=r.get("items",[])
            if not items:return "Não há candidatos de capacidade registrados."
            return "Candidatos de capacidade:\n"+"\n".join(f"• #{x.get('id')} [{x.get('status')}] {x.get('kind')} — {x.get('title')}" for x in items[:30])
        if name=="test_capability_candidate":
            return f"Candidato #{r.get('candidate_id')} validado." if r.get('ok') else f"Candidato não passou na validação: {r.get('test') or r.get('error')}"
        if name=="install_capability_candidate":
            if r.get("ok"):
                return f"Nova competência instalada: {r.get('installed_kind')} `{r.get('installed_id')}`. Ela já pode ser reutilizada em pedidos semelhantes."
            return f"Não consegui instalar a competência: {r.get('error') or r.get('result')}"
        if name=="search_capabilities":
            items = r.get("items", [])
            if not items:
                return "Nenhuma capacidade correspondente foi encontrada."
            lines=[]
            for item in items[:15]:
                required=[k for k,v in item.get("params",{}).items() if v.get("required")]
                req = f" | parâmetros: {', '.join(required)}" if required else ""
                lines.append(f"• {item.get('id')} — {item.get('description')}{req}")
            return "Capacidades encontradas:\n" + "\n".join(lines)
        if name=="execute_capability":
            data = r.get("data")
            text = json.dumps(data, ensure_ascii=False, indent=2, default=str)
            if len(text) > 9000:
                text = text[:9000] + "\n... [resultado truncado]"
            return f"Resultado de {r.get('capability')}:\n{text}"
        if name=="suggest_learned_skills":
            patterns = r.get("patterns", [])
            if not patterns:
                return "Ainda não encontrei padrões repetidos suficientes para sugerir novas Skills."
            lines=[]
            for p in patterns[:8]:
                lines.append(f"• {p.get('occurrences')}x — " + " → ".join(p.get('tools', [])))
            return "Padrões que podem virar Skills:\n" + "\n".join(lines)
        if name=="discover_public_apis":
            items = r.get("items", [])
            if not items:
                return "Nenhuma API pública correspondente foi encontrada no diretório."
            return "APIs públicas encontradas:\n" + "\n".join(
                f"• {i.get('title')} — {i.get('spec_url')}" for i in items[:10]
            )
        if name=="import_openapi":
            return f"Importadas {r.get('imported',0)} novas capacidades. Total do catálogo do usuário: {r.get('user_capabilities',0)}."

        if name=="set_task_plan":
            steps = r.get("steps", [])
            return "Plano definido:\n" + "\n".join(f"{i+1}. {s}" for i,s in enumerate(steps))
        if name=="get_world_state":
            return "Estado atual:\n" + json.dumps(r.get("state",{}), ensure_ascii=False, indent=2, default=str)
        if name=="workflow_stats":
            return f"Workflow Hub: {r.get('workflows',0)} workflows em {len(r.get('groups',{}))} grupos."
        if name=="search_workflows":
            items = r.get("items", [])
            if not items:
                return "Nenhum workflow correspondente foi encontrado."
            return "Workflows encontrados:\n" + "\n".join(
                f"• {i.get('id')} — {i.get('description')} ({i.get('steps')} etapas)" for i in items[:15]
            )
        if name=="execute_workflow":
            if not r.get("ok"):
                return f"Workflow falhou: {r.get('error','erro desconhecido')}"
            return f"Workflow {r.get('name') or r.get('workflow')} concluído com {r.get('steps',0)} etapas."
        if name=="action_stats":
            return (
                f"Action Hub: {r.get('actions',0)} ações locais em "
                f"{len(r.get('engines',{}))} engines e {len(r.get('groups',{}))} grupos."
            )
        if name=="search_actions":
            items = r.get("items", [])
            if not items:
                return "Nenhuma ação correspondente foi encontrada."
            lines = []
            for item in items[:20]:
                required = [k for k,v in item.get("params",{}).items() if v.get("required")]
                req = f" | parâmetros: {', '.join(required)}" if required else ""
                lines.append(
                    f"• {item.get('id')} — {item.get('description')} "
                    f"[{item.get('risk')}]"
                    + req
                )
            return "Ações encontradas:\n" + "\n".join(lines)
        if name=="execute_action":
            payload = {k:v for k,v in r.items() if k not in {"html"}}
            raw = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
            if len(raw) > 9000:
                raw = raw[:9000] + "\n... [resultado truncado]"
            return f"Resultado de {r.get('action','ação')}:\n{raw}"

        return "Tarefa concluída."

    def _tool_result_for_model(self, name, result):
        if name == "execute_action":
            payload = {
                "ok": result.get("ok"),
                "action": result.get("action"),
                "engine": result.get("engine"),
                "error": result.get("error"),
            }
            for key in ("data","items","count","text","url","title","status","path","summary","pages","current"):
                if key in result:
                    payload[key] = result.get(key)
        elif name == "execute_capability":
            payload = {
                "ok": result.get("ok"),
                "capability": result.get("capability"),
                "provider": result.get("provider"),
                "data": result.get("data") if result.get("ok") else None,
                "error": result.get("error"),
            }
        else:
            payload = result
        text = json.dumps(payload, ensure_ascii=False, default=str)
        max_chars = int(self.config.get("agent_tool_result_chars", 7000))
        if len(text) > max_chars:
            text = text[:max_chars] + "... [truncated]"
        return text


    def _run_research_to_file(self, query, status=None):
        """Bounded research pipeline optimized for the CPU-only test machine.

        Search, URL normalization, source ranking, extraction, evidence reduction,
        report generation and verification are deterministic. Qwen is optional and
        sees only a compact evidence pack.
        """
        query = str(query).strip()
        task_id = self.tasks.start(f"Pesquisa estruturada: {query}")
        previous_active = self._active_task_id
        self._active_task_id = task_id
        plan = [
            "Descobrir e normalizar fontes",
            "Priorizar fontes oficiais e confiáveis",
            "Extrair evidências relevantes",
            "Gerar síntese compacta",
            "Salvar relatório auditável",
            "Verificar resultado",
        ]
        self.tasks.set_plan(task_id, plan)
        self.tasks.set_status(task_id, "planning")
        self.diagnostics.event("research_pipeline_start", task_id=task_id, query=query)

        try:
            self._check_cancelled()
            self.tasks.set_status(task_id, "running")
            if status:
                status("Pesquisa: descobrindo fontes")

            search = self.research.search(query, limit=9, official_first=True)
            self.tasks.event(task_id, 1, "research.search", {"query": query}, search)
            if not search.get("ok") or not search.get("items"):
                raise RuntimeError("O Research Engine não encontrou fontes públicas utilizáveis.")
            self.tasks.advance_plan(task_id)

            self._check_cancelled()
            if status:
                status("Pesquisa: priorizando fontes")
            ranked = search.get("items", [])
            official_count = sum(1 for x in ranked if x.get("official"))
            self.tasks.event(
                task_id, 2, "research.rank",
                {"sources": len(ranked)},
                {"ok": True, "official": official_count, "sources": len(ranked)},
            )
            self.tasks.advance_plan(task_id)

            self._check_cancelled()
            if status:
                status("Pesquisa: extraindo evidências")
            bundle = self.research.evidence_pack(query, limit=5, official_first=True)
            self.tasks.event(
                task_id, 3, "research.evidence_pack",
                {"query": query},
                {"ok": bundle.get("ok"), "sources": bundle.get("count", 0)},
            )
            if not bundle.get("ok") or not bundle.get("cards"):
                raise RuntimeError(bundle.get("error") or "Não consegui extrair evidências das fontes encontradas.")
            self.tasks.advance_plan(task_id)

            self._check_cancelled()
            if status:
                status("Pesquisa: sintetizando evidências")

            compact = self.research.compact_evidence(
                bundle,
                max_chars=int(self.config.get("research_evidence_chars", 3600)),
            )
            synthesis = ""
            synthesis_error = None
            research_timeout = int(self.config.get("research_llm_timeout_seconds", 0))
            agent_timeout = int(self.config.get("agent_llm_timeout_seconds", 0))
            if research_timeout > 0 and agent_timeout > 0:
                llm_budget = min(research_timeout, agent_timeout)
            elif research_timeout > 0:
                llm_budget = research_timeout
            elif agent_timeout > 0:
                llm_budget = agent_timeout
            else:
                llm_budget = 0  # execução sem deadline artificial

            try:
                prompt = (
                    "Sintetize SOMENTE as evidências abaixo em português do Brasil. "
                    "Não use conhecimento externo. Não invente datas, números ou obrigações. "
                    "Priorize fontes oficiais quando houver. Estruture em: Visão geral; Pontos principais; "
                    "O que merece verificação adicional. Seja conciso.\n\n"
                    f"TEMA: {query}\n\n{compact}"
                )
                response = self.ollama.chat(
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Você é um sintetizador factual. Use apenas as evidências fornecidas. "
                                "Se as evidências não sustentarem algo, não afirme."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    tools=None,
                    timeout=llm_budget,
                )
                synthesis = ((response.get("message") or {}).get("content") or "").strip()
                synthesis = re.sub(r"<think>.*?</think>", "", synthesis, flags=re.I | re.S).strip()
            except Exception as exc:
                synthesis_error = str(exc)

            # Deterministic summary is already substantially useful, so an LLM
            # timeout no longer degrades the report to raw search snippets.
            if not synthesis:
                synthesis = None

            self.tasks.event(
                task_id, 4, "research.synthesis",
                {"evidence_chars": len(compact), "llm_budget": llm_budget},
                {"ok": True, "llm_used": bool(synthesis), "fallback": not bool(synthesis)},
            )
            self.tasks.advance_plan(task_id)

            self._check_cancelled()
            report = self.research.markdown_report(
                query=query,
                bundle=bundle,
                synthesis=synthesis,
                synthesis_error=synthesis_error,
            )
            slug_result = self.content_studio.execute("slugify", text=query)
            slug = slug_result.get("text") or "pesquisa"
            filename = f"pesquisa_{slug[:70]}.md"

            if status:
                status("Pesquisa: salvando relatório")
            saved = self.files.create_file(filename, report)
            self.tasks.event(task_id, 5, "create_file", {"path": filename}, saved)
            if not saved.get("ok"):
                raise RuntimeError(saved.get("error") or "Falha ao salvar o relatório.")
            self.tasks.advance_plan(task_id)

            self._check_cancelled()
            path = Path(saved.get("path", ""))
            verified = path.is_file() and path.stat().st_size > 100
            verification = {
                "ok": verified,
                "path": str(path),
                "bytes": path.stat().st_size if path.exists() else 0,
            }
            self.tasks.event(task_id, 6, "verify_file", {}, verification)
            if not verified:
                raise RuntimeError("O arquivo foi criado, mas a verificação final falhou.")
            self.tasks.advance_plan(task_id)

            self.research.save_history({
                "query": query,
                "path": str(path),
                "sources": [
                    {
                        "title": c.get("title"),
                        "url": c.get("url"),
                        "domain": c.get("domain"),
                        "authority_score": c.get("authority_score"),
                        "official": c.get("official"),
                    }
                    for c in bundle.get("cards", [])
                ],
                "llm_synthesis": bool(synthesis),
                "synthesis_error": synthesis_error,
            })

            final = (
                f"Pesquisa concluída com {len(bundle.get('cards', []))} fonte(s) analisada(s), "
                f"incluindo {sum(1 for c in bundle.get('cards', []) if c.get('official'))} fonte(s) oficial(is). "
                f"Relatório salvo em: {path}"
            )
            if not synthesis:
                final += " A síntese generativa excedeu o orçamento, mas o Research Engine produziu uma síntese determinística baseada nas evidências extraídas."
            self.tasks.finish(task_id, final, status="completed")
            self.diagnostics.event(
                "research_pipeline_complete",
                task_id=task_id,
                path=str(path),
                sources=len(bundle.get("cards", [])),
                official=sum(1 for c in bundle.get("cards", []) if c.get("official")),
                llm_synthesis=bool(synthesis),
            )
            return final
        except Exception as exc:
            status_name = "cancelled" if "cancelada" in str(exc).lower() else "failed"
            self.tasks.finish(task_id, str(exc), status=status_name)
            self.diagnostics.error("research_pipeline", exc, task_id=task_id, query=query)
            raise RuntimeError(f"Não consegui concluir a pesquisa estruturada: {exc}") from exc
        finally:
            self._active_task_id = previous_active

    def cancel_current(self):
        self._cancel_event.set()
        self.diagnostics.event("cancel_requested", task_id=self._active_task_id)
        return True

    def _check_cancelled(self):
        if self._cancel_event.is_set():
            raise RuntimeError("Tarefa cancelada pelo usuário.")

    def new_conversation(self):
        self.history = []
        result = self.conversations.new_session()
        try:
            pid = self.projects.current_id()
            sid = result.get("session_id")
            if pid and sid:
                self.projects.link_session(pid, sid)
        except Exception:
            pass
        return result

    def delete_conversation(self, session_id):
        sid = int(session_id)
        deleted_was_current = (sid == int(self.conversations.current_session_id))

        try:
            self.projects.unlink_session(sid)
        except Exception:
            pass

        try:
            self.attachments.purge_session(sid)
        except Exception:
            pass

        result = self.conversations.delete_session(sid)
        if not result.get("ok"):
            return result

        current = int(result.get("current") or self.conversations.current_session_id)
        messages = self.conversations.recent_messages(limit=200, session_id=current)
        return {
            **result,
            "deleted_was_current": deleted_was_current,
            "session_id": current,
            "messages": messages,
        }

    def run(self, user_text, status=None, confirm_callback=None):
        """Entrada pública serializada para hardware CPU-first."""
        acquired = False
        while not acquired:
            acquired = self._execution_lock.acquire(timeout=0.25)
            if not acquired and status:
                status("Aguardando o runtime concluir uma etapa em segundo plano")
        try:
            return self._run_unlocked(user_text, status=status, confirm_callback=confirm_callback)
        finally:
            self._execution_lock.release()

    def _run_unlocked(self, user_text, status=None, confirm_callback=None):
        """Entrada pública: persiste conversa e aprendizado explícito."""
        user_text = str(user_text or "").strip()
        if not user_text:
            return "Escreva uma mensagem para continuar."
        try:
            self._last_response_metadata = {}
            answer = self._run_internal(user_text, status=status, confirm_callback=confirm_callback)
            self.conversations.append("user", user_text)
            self.conversations.append("assistant", str(answer), metadata=self._last_response_metadata)
            lesson = self.learning.learn_from_user(user_text)
            self.learning.record_episode(user_text, str(answer), status="completed", metadata={"lesson": lesson})
            reflection = self.reflections.reflect(user_text, str(answer), status="completed", metadata={"lesson": lesson})
            try:
                pid = self.projects.current_id()
                if pid:
                    self.projects.link_session(pid, self.conversations.current_session_id)
            except Exception:
                pass
            if reflection.get("reflection_ids"):
                self.diagnostics.event("reflection_created", reflection_ids=reflection.get("reflection_ids"), prompt=user_text)
            if self.semantic.enabled:
                def _index_episode():
                    try:
                        self.semantic.remember("conversation", f"Usuário: {user_text}\nJarvis: {str(answer)[:5000]}", {"session_id": self.conversations.current_session_id})
                        if lesson.get("learned") and lesson.get("lesson"):
                            self.semantic.remember("lesson", lesson.get("lesson"), {"lesson_id": lesson.get("id")})
                    except Exception:
                        pass
                threading.Thread(target=_index_episode, daemon=True, name="JarvisSemanticMemory").start()
            return answer
        except Exception as exc:
            try:
                self.conversations.append("user", user_text)
                self.conversations.append("assistant", f"[falha] {exc}", metadata={"error": True})
                self.learning.record_episode(user_text, str(exc), status="failed")
                reflection = self.reflections.reflect(user_text, str(exc), status="failed")
                if reflection.get("reflection_ids"):
                    self.improvements.propose(
                        "runtime_failure",
                        "Falha recorrente detectada pelo Jarvis",
                        f"A solicitação falhou e gerou reflexão: {user_text[:300]}",
                        evidence={"error": str(exc), "reflection_ids": reflection.get("reflection_ids")},
                        priority=70,
                    )
            except Exception:
                pass
            raise

    def _run_internal(self, user_text, status=None, confirm_callback=None):
        self._cancel_event.clear()
        started_at = time.monotonic()
        if status:
            status("Processando")

        # Ensino por demonstração: aprende uma rotina observando ações de UI.
        demonstration = self.demonstration_teacher.handle(user_text)
        if demonstration.get("handled"):
            self._last_response_metadata = {"grounded": True, "demonstration_teaching": True}
            return demonstration.get("answer") or "Demonstração atualizada."

        # Modo de ensino/aprendizado persistente vem antes da execução.
        teaching = self.apprenticeship.handle(user_text)
        if teaching.get("handled"):
            self._last_response_metadata = {"grounded": True, "apprenticeship": True}
            return teaching.get("answer") or "Ensino atualizado."

        acquisition_cmd = parse_acquisition_command(user_text)
        if acquisition_cmd:
            action = acquisition_cmd.get("action")
            if action == "resolve":
                if status: status("Capability Resolver: verificando competências existentes")
                result = self.acquisition.resolve(acquisition_cmd.get("goal", ""), create_gap=True)
                self._last_response_metadata = {"grounded": True, "capability_acquisition": True}
                return self.summarize("resolve_capability", result)
            if action == "discover":
                if status: status("Capability Acquisition: procurando como aprender")
                result = self.acquisition.discover(
                    acquisition_cmd.get("goal", ""),
                    source_url=acquisition_cmd.get("source_url"),
                    status=status,
                )
                self._last_response_metadata = {"grounded": True, "capability_acquisition": True}
                if acquisition_cmd.get("auto_install") and result.get("status") == "candidates":
                    safe = next((
                        x for x in result.get("candidates", [])
                        if x.get("kind") == "recipe" and x.get("risk") in {"read", "read_only", "act"}
                    ), None)
                    if safe:
                        if status: status(f"Capability Factory: validando e aprendendo #{safe.get('id')}")
                        installed = self.acquisition.install_candidate(safe.get("id"))
                        if installed.get("ok"):
                            return (
                                self.summarize("install_capability_candidate", installed)
                                + "\n\nA competência foi criada apenas com ferramentas já confiáveis do meu runtime."
                            )
                return self.summarize("acquire_capability", result)
            if action == "gaps":
                return self.summarize("list_capability_gaps", self.acquisition.list_gaps(limit=30))
            if action == "candidates":
                return self.summarize("list_capability_candidates", self.acquisition.list_candidates(limit=30))
            if action == "test":
                return self.summarize("test_capability_candidate", self.acquisition.test_candidate(acquisition_cmd.get("candidate_id")))
            if action == "install":
                cid = acquisition_cmd.get("candidate_id")
                candidates = self.acquisition.list_candidates(limit=100).get("items", [])
                target = next((x for x in candidates if int(x.get("id",0)) == int(cid)), None)
                if not target:
                    return f"Candidato #{cid} não encontrado."
                # O comando só chega aqui quando o usuário pediu explicitamente
                # "instale/aprove a capacidade #N". No desktop ainda mostramos a
                # confirmação visual; clientes sem callback (ex.: Mobile Companion)
                # podem prosseguir porque o consentimento já está no texto do usuário.
                if confirm_callback and not confirm_callback(
                    "Instalar nova competência",
                    f"Instalar o candidato #{cid}: {target.get('title')}?\n\nTipo: {target.get('kind')}\nRisco: {target.get('risk')}"
                ):
                    return "Instalação cancelada."
                if status: status(f"Capability Factory: instalando candidato #{cid}")
                return self.summarize("install_capability_candidate", self.acquisition.install_candidate(cid))

        long_cmd = parse_long_horizon_command(user_text)
        if long_cmd:
            return self._run_long_horizon_command(
                long_cmd, status=status, confirm_callback=confirm_callback
            )

        # Intenções compostas de alta confiança não podem cair no Qwen.
        fast_intent = parse_fast_intent(user_text)
        if fast_intent:
            self.diagnostics.event("fast_intent", prompt=user_text, intent=fast_intent)
            kind = fast_intent.get("kind")
            if kind == "greeting":
                return "Olá. Em que posso ajudar?"
            if kind in {"open_search", "open_url"}:
                result = open_url(fast_intent.get("url", ""))
                if kind == "open_search" and result.get("ok"):
                    return f"Pesquisa aberta no {fast_intent.get('engine','navegador')}: {fast_intent.get('query')}"
                return self.summarize("open_url", result)
            if kind == "web_search":
                result = self.web_search.search(fast_intent.get("query", ""), limit=8)
                return self.summarize("search_web", result)
            if kind == "research_to_file":
                return self._run_research_to_file(fast_intent.get("query", ""), status=status)
            if kind == "diagnose_last_failure":
                recent = self.tasks.recent(limit=20)
                failed = next((x for x in recent if str(x.get("status", "")).lower() == "failed"), None)
                last_error = self.diagnostics.last_error()
                if failed:
                    result = failed.get("final_result") or "Sem detalhe registrado."
                    extra = ""
                    if last_error:
                        extra = f"\nÚltimo erro técnico: {last_error.get('error') or last_error.get('message') or last_error}"
                    return f"A última tarefa com falha foi #{failed.get('id')}: {failed.get('goal')}\nMotivo registrado: {result}{extra}"
                if last_error:
                    return "Não encontrei tarefa marcada como FAILED, mas o último erro técnico foi: " + str(last_error.get("error") or last_error)
                return "Não encontrei uma falha registrada. Abra Diagnóstico se quiser verificar os eventos recentes."

        # Self-awareness vem do estado real do runtime, nunca da imaginação do modelo.
        if self.self_awareness.matches(user_text):
            self._last_response_metadata = {"grounded": True, "runtime_grounded": True}
            return self.self_awareness.answer(user_text)

        # Consultas/análises de serviços cotidianos usam Browser Agent + FAST model,
        # evitando mandar um pedido simples para o reasoning model de 4B.
        if self.service_runtime.matches(user_text):
            result = self.service_runtime.run(user_text, status=status)
            source = result.get("source")
            self._last_response_metadata = {
                "model": result.get("model"),
                "grounded": bool(result.get("grounded")),
                "fallback": bool(result.get("fallback")),
                "sources": [{"title": result.get("service",{}).get("name","Serviço institucional"), "url": source}] if source else [],
            }
            return result.get("answer") or result.get("error") or "Não consegui consultar o serviço."

        # Serviços cotidianos conhecidos do SindPetshop-SP têm Fast Path próprio.
        service_cmd = self.services.parse_open_command(user_text)
        if service_cmd:
            result = self.services.open(service_cmd.get("query",""))
            if result.get("ok"):
                return f"Abrindo {result.get('name')}: {result.get('url')}"
            return result.get("error") or "Não consegui abrir o serviço."

        # Comandos explícitos continuam rápidos e não chamam o modelo.
        task_cmd = parse_task_command(user_text)
        if task_cmd:
            if task_cmd.get("action") == "data_path":
                return f"Meus dados persistentes ficam em: {self.persistent_root}"
            if task_cmd.get("action") == "backup_data":
                result = backup_data(self.persistent_root, self.workspace / "JarvisBackups")
                return (
                    f"Backup criado: {result.get('path')}"
                    if result.get("ok") else f"Não consegui criar o backup: {result.get('error')}"
                )
            if task_cmd.get("action") == "active":
                item = self.tasks.active()
                return (
                    f"Tarefa ativa: {item.get('goal')} (status: {item.get('status')})"
                    if item else "Não há tarefa ativa."
                )
            if task_cmd.get("action") == "recent":
                items = self.tasks.recent(limit=task_cmd.get("limit", 10))
                if not items:
                    return "Ainda não há tarefas registradas."
                return "Tarefas recentes:\n" + "\n".join(
                    f"• #{x.get('id')} [{x.get('status')}] {x.get('goal')}" for x in items
                )

        workflow_cmd = parse_workflow_command(user_text)
        if workflow_cmd:
            action = workflow_cmd.get("action")
            if action == "error":
                return workflow_cmd.get("error")
            if action == "stats":
                return self.summarize("workflow_stats", self.workflows.stats())
            if action == "search":
                return self.summarize("search_workflows", self.workflows.search(workflow_cmd.get("query", ""), 20))
            if action == "execute":
                result = self.dispatch(
                    "execute_workflow",
                    {"workflow_id": workflow_cmd.get("id"), "params": workflow_cmd.get("params", {})},
                    confirm_callback=confirm_callback,
                    source="workflow_explicit",
                )
                return self.summarize("execute_workflow", result)

        action_cmd = parse_action_command(user_text)
        if action_cmd:
            return self._run_action_command(action_cmd, status, confirm_callback)

        capability_cmd = parse_capability_command(user_text)
        if capability_cmd:
            return self._run_capability_command(capability_cmd, status, confirm_callback)

        access_cmd = parse_access_command(user_text)
        if access_cmd:
            if status:
                status("Acesso profundo")
            return self._run_access_command(access_cmd, status=status, confirm_callback=confirm_callback)

        skill_cmd = parse_skill_command(user_text)
        if skill_cmd:
            if status:
                status("Gerenciando skills")
            return self._run_skill_command(skill_cmd, status=status, confirm_callback=confirm_callback)

        mem_cmd = parse_memory_command(user_text)
        if mem_cmd:
            if status:
                status("Atualizando memória")
            return self._run_memory_command(mem_cmd)

        direct = fast_path(user_text, self.desktop)
        if direct:
            n, a = direct
            return self.summarize(n, self.dispatch(n, a, confirm_callback=confirm_callback, source="fast_path"))

        # Conversa e perguntas informativas usam runtime leve; demandas realmente
        # complexas podem acionar o Swarm mesmo sem ferramentas externas.
        selected_tools = self._tools_for_prompt(user_text)
        swarm_candidate = self.swarm.should_swarm(user_text, selected_tools)
        if self.conversation_answer.should_handle(user_text, selected_tools):
            if swarm_candidate:
                if status:
                    status("Orquestrando especialistas")
                base_context = self.context_orchestrator.build(
                    user_text, max_chars=int(self.config.get("swarm_context_chars", 5200))
                ).get("text", "")
                result = self.swarm.solve(user_text, base_context=base_context, status=status)
                self._last_response_metadata = {
                    "model": self.models.reason_model_name(),
                    "grounded": True,
                    "swarm": True,
                    "swarm_roles": result.get("roles", []),
                    "swarm_session_id": result.get("session_id"),
                }
                self.swarm.finish(result, status="completed", success=True)
                self.diagnostics.event(
                    "swarm_answer", prompt=user_text, roles=result.get("roles", []),
                    session_id=result.get("session_id")
                )
                return result.get("answer") or "Não consegui sintetizar uma resposta."

            if status:
                status("Conversando")
            result = self.conversation_answer.answer(user_text)
            self._last_response_metadata = {
                "model": result.get("model"),
                "grounded": bool(result.get("grounded")),
                "fallback": bool(result.get("fallback")),
                "sources": result.get("sources") or [],
            }
            self.diagnostics.event(
                "conversation_answer",
                prompt=user_text,
                model=result.get("model"),
                grounded=result.get("grounded"),
                fallback=result.get("fallback"),
            )
            return result.get("answer") or "Não consegui formular uma resposta."

        # Agent Runtime: mantém a tarefa e permite vários ciclos ferramenta -> observação -> decisão.
        task_id = self.tasks.start(user_text)
        self._active_task_id = task_id
        self.diagnostics.event("task_start", task_id=task_id, prompt=user_text)
        conversation_context = self.conversations.context_messages(
            user_text,
            recent_limit=int(self.config.get("conversation_recent_limit", 6)),
            relevant_limit=int(self.config.get("conversation_relevant_limit", 4)),
            max_chars=int(self.config.get("conversation_context_chars", 3600)),
        )
        semantic_context = []
        if self.semantic.enabled:
            try:
                sem = self.semantic.search(user_text, limit=3)
                items = sem.get("items", []) if sem.get("ok") else []
                if items:
                    compact = "\n".join(f"- {x.get('text','')[:550]}" for x in items)
                    semantic_context = [{"role":"system","content":"Memórias semanticamente relacionadas (use apenas se relevantes):\n" + compact}]
            except Exception:
                semantic_context = []
        swarm_bundle = None
        swarm_context_messages = []
        if swarm_candidate:
            if status:
                status("Orquestrando especialistas")
            base_context = self.context_orchestrator.build(
                user_text, max_chars=int(self.config.get("swarm_context_chars", 5200))
            ).get("text", "")
            swarm_bundle = self.swarm.prepare(user_text, base_context=base_context, status=status)
            swarm_context_messages = [{
                "role": "system",
                "content": (
                    "SWARM BLACKBOARD — orientação interna para esta tarefa. Não exponha a discussão entre agentes ao usuário.\n"
                    + swarm_bundle.get("context", "")
                )
            }]

        messages = [{"role":"system","content":self.system_prompt(user_text)}] + swarm_context_messages + semantic_context + conversation_context + [{"role":"user","content":user_text}]

        max_rounds = int(self.config.get("agent_max_rounds", 4))
        total_tool_calls = 0
        max_tool_calls = int(self.config.get("agent_max_tool_calls", 10))
        llm_timeout = int(self.config.get("agent_llm_timeout_seconds", 0))
        total_budget = int(self.config.get("agent_total_timeout_seconds", 0))
        last_summaries = []

        try:
            for round_index in range(1, max_rounds + 1):
                self._check_cancelled()
                elapsed = time.monotonic() - started_at

                # total_budget <= 0 significa que a tarefa não é interrompida
                # automaticamente por tempo. O usuário decide quando parar.
                if total_budget > 0 and elapsed >= total_budget:
                    raise RuntimeError(
                        f"A tarefa ultrapassou o limite configurado de {total_budget}s."
                    )

                model_name = self.models.reason_model_name()
                if status:
                    status(
                        f"Pensando com {model_name} • ciclo {round_index}/{max_rounds}"
                    )

                if total_budget > 0:
                    remaining_budget = max(1, int(total_budget - elapsed))
                    if llm_timeout > 0:
                        remaining = min(llm_timeout, remaining_budget)
                    else:
                        remaining = remaining_budget
                else:
                    remaining = llm_timeout  # 0 = sem timeout no OllamaClient

                resp = self.ollama.chat(
                    messages=messages,
                    tools=self._tools_for_prompt(user_text),
                    timeout=remaining,
                    model=model_name,
                )
                msg = resp.get("message", {})
                calls = msg.get("tool_calls") or []

                if not calls:
                    ans = (msg.get("content") or "").strip()
                    ans = re.sub(r"<think>.*?</think>", "", ans, flags=re.I | re.S).strip()
                    if not ans and last_summaries:
                        ans = "\n".join(last_summaries[-3:])
                    ans = ans or "Não recebi uma resposta válida."
                    if swarm_bundle:
                        ans = self.swarm.review(
                            user_text, ans, bundle=swarm_bundle,
                            tool_summaries=last_summaries, status=status
                        )
                        self.swarm.blackboard.add(swarm_bundle["session_id"], "executor", "answer", ans)
                        self.swarm.finish(swarm_bundle, status="completed", success=True)
                        self._last_response_metadata.update({
                            "swarm": True,
                            "swarm_roles": swarm_bundle.get("roles", []),
                            "swarm_session_id": swarm_bundle.get("session_id"),
                        })
                    self.tasks.finish(task_id, ans, status="completed")
                    if total_tool_calls >= 2:
                        try:
                            self.memory.remember(
                                f"Tarefa concluída: {user_text}. Resultado: {ans[:700]}",
                                key=f"task:{task_id}",
                                kind="episode",
                            )
                        except Exception:
                            pass
                    self.history += [
                        {"role":"user","content":user_text},
                        {"role":"assistant","content":ans},
                    ]
                    self.history = self.history[-12:]
                    self.diagnostics.event(
                        "task_complete", task_id=task_id,
                        elapsed_ms=round((time.monotonic()-started_at)*1000,1),
                        tool_calls=total_tool_calls,
                    )
                    self._active_task_id = None
                    return ans

                # Preserve assistant tool call message so Qwen can continue from its own action.
                messages.append(msg)

                for call in calls:
                    self._check_cancelled()
                    if total_tool_calls >= max_tool_calls:
                        break
                    f = call.get("function", {})
                    name = f.get("name")
                    args = f.get("arguments", {}) or {}
                    total_tool_calls += 1

                    if status:
                        status(f"Agente executando: {name}")

                    result = self.dispatch(
                        name, args, confirm_callback=confirm_callback, source="agent_runtime"
                    )

                    verification = self.verifier.verify(name, args, result)
                    if result.get("ok") and not verification.get("verified"):
                        result = dict(result)
                        result["ok"] = False
                        result["error"] = "Verificação pós-ação falhou: " + verification.get("reason", "")
                    else:
                        result = dict(result)
                        result["verification"] = verification

                    self.tasks.event(task_id, total_tool_calls, name, args, result)

                    if result.get("ok") and name not in {
                        "set_task_plan", "get_world_state",
                        "search_actions", "search_capabilities",
                        "action_stats", "capability_stats",
                    }:
                        current = self.tasks.get(task_id)
                        if current and current.get("plan"):
                            self.tasks.advance_plan(task_id)

                    summary = self.summarize(name, result)
                    last_summaries.append(summary)

                    messages.append({
                        "role":"tool",
                        "tool_name": name,
                        "content": self._tool_result_for_model(name, result),
                    })

                # Contexto pequeno no hardware atual: preserva sistema + objetivo + ciclos recentes.
                if len(messages) > 12:
                    system_msg = messages[0]
                    goal_msg = {"role":"user","content":user_text}
                    messages = [system_msg, goal_msg] + messages[-8:]

                if total_tool_calls >= max_tool_calls:
                    break

            final = (
                "A tarefa atingiu o limite estrutural desta execução. "
                f"Foram executadas {total_tool_calls} ações."
            )

            handoff = None
            if self.config.get("long_horizon_auto_handoff_on_agent_limit", True):
                try:
                    current_task = self.tasks.get(task_id) or {}
                    full_plan = current_task.get("plan") or []
                    current_index = int(current_task.get("current_step") or 0)
                    remaining_plan = full_plan[current_index:] if full_plan else []
                    metadata = {
                        "source_task_id": task_id,
                        "tool_calls_before_handoff": total_tool_calls,
                        "previous_summaries": last_summaries[-5:],
                    }
                    handoff = self.long_horizon.create(
                        user_text,
                        plan=remaining_plan if remaining_plan else None,
                        project_id=self.projects.current_id(),
                        session_id=self.conversations.current_session_id,
                        auto_resume=True,
                        priority=65,
                        metadata=metadata,
                    )
                except Exception as exc:
                    self.diagnostics.error("long_horizon_handoff", exc, task_id=task_id)

            if handoff and handoff.get("ok"):
                jid = handoff.get("data",{}).get("id")
                final += (
                    f"\n\nPara não abandonar o objetivo, converti a continuação em Job persistente #{jid}. "
                    "Ele continuará em checkpoints e poderá sobreviver a reinícios."
                )
                self.tasks.finish(task_id, final, status="completed")
            else:
                final += "\n" + "\n".join(last_summaries[-3:])
                self.tasks.finish(task_id, final, status="paused")
                try:
                    self.acquisition.record_failure(user_text, final)
                except Exception:
                    pass

            if swarm_bundle:
                self.swarm.finish(
                    swarm_bundle,
                    status="completed" if handoff and handoff.get("ok") else "paused",
                    success=bool(handoff and handoff.get("ok"))
                )
            self.diagnostics.event(
                "task_handoff" if handoff and handoff.get("ok") else "task_paused",
                task_id=task_id, tool_calls=total_tool_calls,
                long_job_id=(handoff.get("data",{}).get("id") if handoff and handoff.get("ok") else None)
            )
            self._active_task_id = None
            return final
        except Exception as exc:
            self.tasks.finish(task_id, str(exc), status="failed")
            try:
                self.acquisition.record_failure(user_text, str(exc))
            except Exception:
                pass
            if 'swarm_bundle' in locals() and swarm_bundle:
                try:
                    self.swarm.finish(swarm_bundle, status="failed", success=False)
                except Exception:
                    pass
            self.diagnostics.error(
                "agent_run", exc, task_id=task_id, prompt=user_text,
                elapsed_ms=round((time.monotonic()-started_at)*1000,1),
                tool_calls=total_tool_calls,
            )
            self._active_task_id = None
            raise

