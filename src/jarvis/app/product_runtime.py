from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os

from jarvis.a2a import A2ARegistry,RemoteAgent
from jarvis.agents import (
    AgentRegistry,ResearchAgent,AnalystAgent,CreatorAgent,DeveloperAgent,
    OperatorAgent,ReviewerAgent,MemoryCuratorAgent,InboxAgent,AgentFactory,AgencyAgentCatalog,AgentRouter,builtin_agent_cards
)
from jarvis.artifacts import ArtifactStore
from jarvis.brain import ChatService,IntentRouter,JarvisOrchestrator,ToolPlanner
from jarvis.briefing import BriefingService
from jarvis.browser import PlaywrightBrowserController
from jarvis.capabilities.resolver import CapabilityResolver
from jarvis.connectors import (
    ConnectorRegistry,ConnectorRepository,ConnectorService,
    LocalInboxConnector,ICSCalendarConnector,
    GoogleOAuthClient,GoogleTokenStore,GmailConnector,GoogleCalendarConnector
)
from jarvis.distributed import NodeRepository,NodeRegistry,DistributedDispatcher
from jarvis.hq import HQService
from jarvis.mcp import MCPRegistry,MCPServer
from jarvis.memory import MemoryService
from jarvis.missions import TeamMissionService,MissionPlanner
from jarvis.proactivity import OpportunityEngine
from jarvis.models import (
    ModelRegistry,ModelRouter,OllamaProvider,OpenAICompatibleProvider,NvidiaNemotronProvider
)
from jarvis.runtime import GoalVerifier,ObserveActVerifyRuntime
from jarvis.integrations import AIMesh,CreativeStudioClient,HermesAgentBridge,WhatsAppGatewayClient
from jarvis.scheduler import SchedulerRepository,Scheduler
from jarvis.security import PolicyEngine,SecretStore
from jarvis.skills import SkillRegistry,SkillRepository,SkillManager,SkillRunner,SkillGenerationService
from jarvis.storage.repositories.preferences import PreferenceRepository
from jarvis.storage.repositories.product import (
    AgentRunRepository,ApprovalRepository,ArtifactRepository,ConversationRepository,
    MemoryRepository,MissionRepository,ToolRunRepository,WorkspaceRepository,
    ProjectRepository,WorkspaceNoteRepository
)
from jarvis.tools import (
    ListDirectoryTool,ReadTextFileTool,SystemTimeTool,ToolExecutor,ToolRegistry,
    WriteWorkspaceTextTool,WriteWorkspacePdfTool,WebSearchTool,WebFetchTool,
    BrowserOpenTool,BrowserSnapshotTool,BrowserFillTool,BrowserClickTool,
    WindowsListTool,WindowsInspectTool,WindowsActivateTool,WindowsSetTextTool,
    WindowsClickTool,WhatsAppSendMessageTool,MCPToolAdapter
)
from jarvis.voice import VoiceService
from jarvis.watchers import WatcherRepository,WatcherService
from jarvis.windows import WindowsUIAController,WhatsAppDesktopService
from .bootstrap import Runtime,start_runtime


def _load_json(path:Path,default):
    try:
        if path.is_file():
            return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default
    return default


@dataclass(slots=True)
class ProductRuntime:
    foundation:Runtime
    model_registry:ModelRegistry
    model_router:ModelRouter
    ai_mesh:AIMesh
    agent_registry:AgentRegistry
    tool_registry:ToolRegistry
    tool_executor:ToolExecutor
    memory:MemoryService
    chat:ChatService
    conversations:ConversationRepository
    preferences:PreferenceRepository
    orchestrator:JarvisOrchestrator
    tool_planner:ToolPlanner
    hq:HQService
    policy:PolicyEngine
    missions:TeamMissionService
    briefing:BriefingService
    workspace:dict
    approvals:ApprovalRepository
    tool_runs:ToolRunRepository
    connector_registry:ConnectorRegistry
    connector_repository:ConnectorRepository
    connectors:ConnectorService
    watcher_repository:WatcherRepository
    watchers:WatcherService
    scheduler_repository:SchedulerRepository
    scheduler:Scheduler
    browser:PlaywrightBrowserController
    windows:WindowsUIAController
    whatsapp:WhatsAppDesktopService
    voice:VoiceService
    skill_registry:SkillRegistry
    skill_manager:SkillManager
    skill_runner:SkillRunner
    skill_generator:SkillGenerationService
    capabilities:CapabilityResolver
    mcp:MCPRegistry
    a2a:A2ARegistry
    nodes:NodeRegistry
    dispatcher:DistributedDispatcher
    secret_store:SecretStore
    google_oauth:GoogleOAuthClient
    projects:ProjectRepository
    workspace_notes:WorkspaceNoteRepository
    opportunities:OpportunityEngine
    agent_factory:AgentFactory
    agency_catalog:AgencyAgentCatalog
    agent_router:AgentRouter
    goal_verifier:GoalVerifier
    action_runtime:ObserveActVerifyRuntime

    async def close(self):
        try:
            await self.browser.close()
        except Exception:
            pass
        try:
            self.mcp.close()
        except Exception:
            pass
        await self.foundation.close()


async def start_product_runtime(data_dir:Path|None=None,*,model_provider=None):
    foundation=await start_runtime(data_dir)
    try:
        cfg=foundation.config
        conn=foundation.database.conn()

        conversations=ConversationRepository(conn)
        preferences=PreferenceRepository(conn)
        agent_runs=AgentRunRepository(conn)
        artifact_repo=ArtifactRepository(conn)
        memory_repo=MemoryRepository(conn)
        approvals=ApprovalRepository(conn)
        tool_runs=ToolRunRepository(conn)
        mission_repo=MissionRepository(conn)
        workspace_repo=WorkspaceRepository(conn)
        project_repo=ProjectRepository(conn)
        notes_repo=WorkspaceNoteRepository(conn)
        workspace=workspace_repo.get_or_create_default()

        secret_store=SecretStore(cfg.data_dir/'secrets')
        nvidia_key=secret_store.get('nvidia_api_key') or os.environ.get('NVIDIA_API_KEY','')
        wa_key=secret_store.get('wa_akg_api_key') or os.environ.get('JARVIS_WA_AKG_KEY','')
        creative_key=secret_store.get('creative_api_key') or os.environ.get('JARVIS_CREATIVE_API_KEY','')
        ai_mesh=AIMesh(
            hermes=HermesAgentBridge(
                command=cfg.ai.hermes_command,
                profile=cfg.ai.hermes_profile,
                toolsets=cfg.ai.hermes_toolsets,
                timeout_seconds=cfg.ai.hermes_timeout_seconds,
                enabled=cfg.ai.hermes_enabled,
            ),
            whatsapp_gateway=WhatsAppGatewayClient(
                base_url=cfg.ai.wa_akg_url,
                api_key=wa_key,
                session_id=cfg.ai.wa_akg_session,
                timeout_seconds=cfg.ai.wa_akg_timeout_seconds,
            ),
            creative=CreativeStudioClient(
                base_url=cfg.ai.creative_api_url,
                api_key=creative_key,
                timeout_seconds=cfg.ai.creative_timeout_seconds,
                poll_seconds=cfg.ai.creative_poll_seconds,
                max_polls=cfg.ai.creative_max_polls,
            ),
        )
        artifact_store=ArtifactStore(cfg.artifacts_dir,artifact_repo)
        memory=MemoryService(memory_repo)

        # Model Mesh: local first. Optional cloud adapters are additive.
        models=ModelRegistry()
        provider=model_provider or OllamaProvider(
            cfg.models.ollama_url,cfg.models.default_model,
            timeout_seconds=cfg.models.timeout_seconds,
            context_tokens=cfg.models.context_tokens,
            temperature=cfg.models.temperature
        )
        models.register(provider,{
            'local':provider.provider_id=='ollama',
            'paid':False,
            'capabilities':['chat','reasoning','creative','coding','tool_use','general'],
        })

        external_key=secret_store.get('openai_compatible_api_key') or os.environ.get('JARVIS_OPENAI_API_KEY')
        external_base=os.environ.get('JARVIS_OPENAI_BASE_URL')
        external_model=os.environ.get('JARVIS_OPENAI_MODEL')
        if (not cfg.local_only) and external_base and external_model:
            models.register(
                OpenAICompatibleProvider(
                    'openai_compatible',external_base,external_key or '',
                    external_model,timeout=120
                ),
                {
                    'local':False,'paid':True,
                    'capabilities':['chat','reasoning','creative','coding','tool_use','general'],
                }
            )

        if (not cfg.local_only) and cfg.ai.nvidia_enabled:
            models.register(
                NvidiaNemotronProvider(
                    cfg.ai.nvidia_base_url,nvidia_key,cfg.ai.nvidia_model,
                    timeout=cfg.models.timeout_seconds,
                    enable_thinking=cfg.ai.nvidia_thinking,
                    max_tokens=cfg.ai.nvidia_max_tokens,
                    thinking_token_budget=cfg.ai.nvidia_thinking_token_budget,
                ),
                {
                    'local':False,
                    'paid':True,
                    'capabilities':['chat','reasoning','coding','tool_use','general'],
                }
            )

        premium_provider='nvidia_nemotron' if nvidia_key and not cfg.local_only and cfg.ai.nvidia_enabled else None
        router=ModelRouter(
            provider.provider_id,
            getattr(provider,'default_model',cfg.models.default_model),
            registry=models,
            premium_provider=premium_provider,
            privacy_mode=cfg.privacy.mode,
        )

        policy=PolicyEngine()
        browser=PlaywrightBrowserController(headless=False)
        windows=WindowsUIAController()
        whatsapp=WhatsAppDesktopService()
        voice=VoiceService()

        tools=ToolRegistry()
        tools.register(SystemTimeTool())
        tools.register(ReadTextFileTool())
        tools.register(ListDirectoryTool())
        tools.register(WriteWorkspaceTextTool(cfg.data_dir/'workspace_files'))
        tools.register(WriteWorkspacePdfTool(cfg.data_dir/'workspace_files'))
        if not cfg.local_only:
            tools.register(WebSearchTool())
            tools.register(WebFetchTool())
            tools.register(BrowserOpenTool(browser))
            tools.register(BrowserSnapshotTool(browser))
            tools.register(BrowserFillTool(browser))
            tools.register(BrowserClickTool(browser))
        tools.register(WindowsListTool(windows))
        tools.register(WindowsInspectTool(windows))
        tools.register(WindowsActivateTool(windows))
        tools.register(WindowsSetTextTool(windows))
        tools.register(WindowsClickTool(windows))
        if not cfg.local_only:
            tools.register(WhatsAppSendMessageTool(whatsapp))
        tool_executor=ToolExecutor(
            registry=tools,policy=policy,approvals=approvals,
            tool_runs=tool_runs,bus=foundation.bus
        )
        goal_verifier=GoalVerifier()
        action_runtime=ObserveActVerifyRuntime(
            tool_executor=tool_executor,verifier=goal_verifier
        )

        # Connector layer. Google connectors always exist but safely remain
        # unconfigured until OAuth credentials are supplied.
        connector_registry=ConnectorRegistry()
        connector_repo=ConnectorRepository(conn)
        connector_service=ConnectorService(
            registry=connector_registry,repository=connector_repo,bus=foundation.bus
        )
        inbox_path=cfg.data_dir/'connectors'/'inbox'
        calendar_path=cfg.data_dir/'connectors'/'calendar.ics'
        connector_service.register(
            LocalInboxConnector(inbox_path),
            config={'path':str(inbox_path),'mode':'read_only'}
        )
        connector_service.register(
            ICSCalendarConnector(calendar_path),
            config={'path':str(calendar_path),'mode':'read_only'}
        )
        google_oauth=GoogleOAuthClient(
            cfg.data_dir/'config'/'google_client.json',
            GoogleTokenStore(cfg.data_dir/'secrets'/'google_token.bin'),
        )
        if not cfg.local_only:
            connector_service.register(
                GmailConnector(google_oauth),
                config={'mode':'read_only','oauth':'google'}
            )
            connector_service.register(
                GoogleCalendarConnector(google_oauth),
                config={'mode':'read_only','oauth':'google'}
            )

        watcher_repo=WatcherRepository(conn)
        watchers=WatcherService(
            repository=watcher_repo,
            connector_repository=connector_repo,
            bus=foundation.bus
        )
        watchers.ensure_defaults()

        scheduler_repo=SchedulerRepository(conn)
        scheduler=Scheduler(
            repository=scheduler_repo,connectors=connector_service,
            watchers=watchers,bus=foundation.bus
        )
        scheduler.ensure_defaults()

        # Optional external connectors cannot break startup.
        await connector_service.sync_all()
        await watchers.check_all()

        # Skills/capabilities.
        skill_registry=SkillRegistry()
        skill_repository=SkillRepository(conn)
        skill_manager=SkillManager(
            root=cfg.data_dir/'skills',
            staging=cfg.data_dir/'skill_staging',
            repository=skill_repository,
            registry=skill_registry,
        )
        skill_runner=SkillRunner(skill_registry)
        skill_generator=SkillGenerationService(
            skill_manager=skill_manager,
            model_registry=models,
            model_router=router,
        )

        # External agent/tool ecosystems.
        mcp=MCPRegistry()
        mcp_cfg=[] if cfg.local_only else _load_json(cfg.data_dir/'config'/'mcp_servers.json',[])
        for item in mcp_cfg if isinstance(mcp_cfg,list) else []:
            try:
                server=MCPServer(
                    str(item['id']),list(item['command']),
                    bool(item.get('enabled',True)),
                    item.get('env'),
                )
                mcp.register(server)
                client=mcp.client(server.server_id)
                for tool_name in item.get('tools') or []:
                    tools.register(MCPToolAdapter(
                        server.server_id,str(tool_name),client
                    ))
            except Exception:
                continue

        a2a=A2ARegistry()
        a2a_cfg=[] if cfg.local_only else _load_json(cfg.data_dir/'config'/'remote_agents.json',[])
        for item in a2a_cfg if isinstance(a2a_cfg,list) else []:
            try:
                token=None
                if item.get('token_secret'):
                    token=secret_store.get(str(item['token_secret']))
                a2a.register(RemoteAgent(
                    str(item['id']),str(item['endpoint']),
                    bool(item.get('enabled',True)),token
                ))
            except Exception:
                continue

        node_repository=NodeRepository(conn)
        nodes=NodeRegistry(node_repository)
        dispatcher=DistributedDispatcher(nodes)

        agents=AgentRegistry()
        for card in builtin_agent_cards():
            agents.register_card(card)

        llm_kwargs=dict(
            model_registry=models,model_router=router,
            artifact_store=artifact_store,agent_runs=agent_runs,
            bus=foundation.bus
        )
        agents.register_runtime('research.general',ResearchAgent(
            **llm_kwargs,tool_executor=tool_executor,
            web_enabled=((model_provider is None) and (not cfg.local_only))
        ))
        agents.register_runtime('intelligence.analyst',AnalystAgent(**llm_kwargs))
        agents.register_runtime('creative.creator',CreatorAgent(**llm_kwargs))
        agents.register_runtime('engineering.developer',DeveloperAgent(**llm_kwargs))
        agents.register_runtime('review.verifier',ReviewerAgent(**llm_kwargs))
        agents.register_runtime('operations.operator',OperatorAgent(
            tool_executor=tool_executor,agent_runs=agent_runs,bus=foundation.bus,
            task_service=foundation.task_service,goal_verifier=goal_verifier
        ))
        agents.register_runtime('memory.curator',MemoryCuratorAgent(
            memory_repository=memory_repo,artifact_store=artifact_store,
            agent_runs=agent_runs,bus=foundation.bus
        ))
        agents.register_runtime('administration.inbox',InboxAgent(
            connector_repository=connector_repo,artifact_store=artifact_store,
            agent_runs=agent_runs,bus=foundation.bus
        ))
        agent_factory=AgentFactory(
            path=cfg.data_dir/'agents'/'custom_agents.json',
            registry=agents,llm_kwargs=llm_kwargs
        )

        # Agency Agents / Codex bridge. Definitions are imported as read-only
        # knowledge specialists; they never inherit Operator tools or permissions.
        agency_catalog=AgencyAgentCatalog()
        agency_catalog.register(agents,llm_kwargs)
        agent_router=AgentRouter(registry=agents,agency_catalog=agency_catalog)

        capabilities=CapabilityResolver(
            agents=agents,tools=tools,skills=skill_registry,
            connectors=connector_service
        )
        local_caps=set(tools.list_ids())
        for card in agents.cards():
            local_caps.update(card.capabilities)
        nodes.register_local(capabilities=tuple(sorted(local_caps)))

        # External specialists participate automatically only in real runtime.
        # Test/mock providers stay hermetic and deterministic.
        mission_planner=MissionPlanner(
            specialist_router=agent_router if (model_provider is None and agency_catalog.definitions()) else None,
            specialist_limit=1,
        )
        team_missions=TeamMissionService(
            agent_registry=agents,task_service=foundation.task_service,
            missions=mission_repo,bus=foundation.bus,
            workspace_id=workspace['workspace_id'],planner=mission_planner
        )
        tool_planner=ToolPlanner(
            model_registry=models,model_router=router,tool_registry=tools
        )

        briefing=BriefingService(
            tasks=foundation.tasks,approvals=approvals,artifacts=artifact_repo,
            missions=mission_repo,model_registry=models,
            connector_repository=connector_repo,
            connector_service=connector_service,
            watcher_repository=watcher_repo
        )
        opportunities=OpportunityEngine(
            briefing=briefing,tasks=foundation.tasks
        )
        orchestrator=JarvisOrchestrator(
            intent_router=IntentRouter(),model_registry=models,model_router=router,
            ai_mesh=ai_mesh,
            agent_registry=agents,task_service=foundation.task_service,
            memory=memory,bus=foundation.bus,team_missions=team_missions,
            briefing=briefing,tool_planner=tool_planner
        )
        chat=ChatService(conversations,orchestrator)
        hq=HQService(
            agent_runs,foundation.tasks,approvals,foundation.events,
            missions=mission_repo,workspace=workspace,
            connector_repository=connector_repo,
            watcher_repository=watcher_repo,agent_registry=agents
        )

        return ProductRuntime(
            foundation,models,router,ai_mesh,agents,tools,tool_executor,memory,chat,conversations,preferences,
            orchestrator,tool_planner,hq,policy,team_missions,briefing,workspace,approvals,tool_runs,
            connector_registry,connector_repo,connector_service,
            watcher_repo,watchers,scheduler_repo,scheduler,
            browser,windows,whatsapp,voice,skill_registry,skill_manager,skill_runner,skill_generator,
            capabilities,mcp,a2a,nodes,dispatcher,secret_store,google_oauth,
            project_repo,notes_repo,opportunities,agent_factory,agency_catalog,agent_router,goal_verifier,action_runtime
        )
    except Exception:
        await foundation.close()
        raise
