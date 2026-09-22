import json
from pathlib import Path
from browser_agent.engine import BrowserAgent
from runtime.task_store import TaskStore
from runtime.diagnostics import RuntimeDiagnostics
from supervisor.engine import RuntimeSupervisor

home=Path.home()
workspace=home/'JarvisWorkspace'; workspace.mkdir(exist_ok=True)
root=home/'JarvisData'; root.mkdir(exist_ok=True)
base=Path(__file__).resolve().parent
sup=RuntimeSupervisor(
    config={'model':'qwen3:4b','num_ctx':4096,'agent_llm_timeout_seconds':40,'agent_total_timeout_seconds':105,'agent_max_rounds':4,'agent_max_tool_calls':10},
    persistent_root=root, workspace=workspace,
    tasks=TaskStore(root/'tasks'/'jarvis_tasks.db'), diagnostics=RuntimeDiagnostics(root/'logs'),
    browser=BrowserAgent(root/'browser'/'profile',workspace/'JarvisDownloads'),
    ollama_url='http://127.0.0.1:11434/api/chat', base_dir=base,
)
print(json.dumps(sup.full_health(),indent=2,ensure_ascii=False))
