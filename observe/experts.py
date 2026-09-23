APP_EXPERTS = {
    "jarvis": {
        "label": "Jarvis Workspace",
        "domain": "orquestração e conversa",
        "preferred_execution": ["contexto local", "Actions/Skills", "App Experts"],
        "knowledge": ["memória pessoal", "projetos", "procedimentos", "estado operacional"],
        "bridge": "native",
    },
    "photoshop": {
        "label": "Photoshop Expert",
        "domain": "design e edição de imagem",
        "preferred_execution": ["UXP/actionJSON", "batchPlay/API", "UI Automation", "visão+mouse"],
        "knowledge": ["documentação Adobe UXP", "demonstrações do usuário", "arquivos PSD", "experiências aprovadas"],
        "bridge": "planned",
    },
    "vscode": {
        "label": "VSCode Expert",
        "domain": "edição de código e projetos",
        "preferred_execution": ["filesystem", "Git/CLI", "extensão VSCode", "UI Automation"],
        "knowledge": ["workspace", "diffs", "terminal", "histórico de tarefas", "demonstrações"],
        "bridge": "planned",
    },
    "visual_studio": {
        "label": "Visual Studio Expert",
        "domain": "desenvolvimento .NET",
        "preferred_execution": ["filesystem/CLI", "MSBuild/dotnet", "extensão/API", "UI Automation"],
        "knowledge": ["solution/project", "build output", "Git", "demonstrações"],
        "bridge": "planned",
    },
    "chrome": {
        "label": "Browser Expert",
        "domain": "navegação e aplicações web",
        "preferred_execution": ["API/conector", "DOM/Playwright", "Accessibility", "visão+mouse"],
        "knowledge": ["sessão do navegador", "DOM", "documentação web", "experiências"],
        "bridge": "partial",
    },
    "edge": {
        "label": "Browser Expert",
        "domain": "navegação e aplicações web",
        "preferred_execution": ["API/conector", "DOM/Playwright", "Accessibility", "visão+mouse"],
        "knowledge": ["sessão do navegador", "DOM", "documentação web", "experiências"],
        "bridge": "partial",
    },
    "opera": {
        "label": "Browser Expert",
        "domain": "navegação e aplicações web",
        "preferred_execution": ["API/conector", "DOM/Playwright", "Accessibility", "visão+mouse"],
        "knowledge": ["sessão do navegador", "DOM", "documentação web", "experiências"],
        "bridge": "partial",
    },
    "word": {
        "label": "Word Expert",
        "domain": "documentos",
        "preferred_execution": ["Office API/COM", "document engine", "UI Automation"],
        "knowledge": ["documentos anteriores", "templates", "demonstrações"],
        "bridge": "planned",
    },
    "excel": {
        "label": "Excel Expert",
        "domain": "planilhas e análise",
        "preferred_execution": ["Office API/COM", "Python/openpyxl", "UI Automation"],
        "knowledge": ["planilhas anteriores", "fórmulas", "templates", "demonstrações"],
        "bridge": "planned",
    },
    "obs": {
        "label": "OBS Expert",
        "domain": "captura e gravação",
        "preferred_execution": ["obs-websocket/API", "configuração local", "UI Automation"],
        "knowledge": ["cenas", "sources", "perfis", "demonstrações"],
        "bridge": "planned",
    },
    "explorer": {
        "label": "Windows Files Expert",
        "domain": "arquivos e pastas",
        "preferred_execution": ["filesystem", "shell seguro", "UI Automation"],
        "knowledge": ["workspace", "aliases", "histórico de tarefas"],
        "bridge": "native",
    },
    "powershell": {
        "label": "Shell Expert",
        "domain": "linha de comando",
        "preferred_execution": ["comandos permitidos", "scripts versionados", "UI Automation"],
        "knowledge": ["histórico seguro", "workspace", "documentação"],
        "bridge": "partial",
    },
    "cmd": {
        "label": "Shell Expert",
        "domain": "linha de comando",
        "preferred_execution": ["comandos permitidos", "scripts versionados", "UI Automation"],
        "knowledge": ["histórico seguro", "workspace", "documentação"],
        "bridge": "partial",
    },
}


def expert_profile(app_id, observed_events=0, procedures=0, last_seen=None):
    app_id = str(app_id or "unknown")
    base = dict(APP_EXPERTS.get(app_id) or {
        "label": f"{app_id} Expert",
        "domain": "aplicativo observado",
        "preferred_execution": ["API nativa quando disponível", "UI Automation", "visão+mouse"],
        "knowledge": ["demonstrações do usuário", "experiências", "documentação"],
        "bridge": "unknown",
    })

    if procedures >= 3:
        maturity = "practiced"
    elif procedures >= 1:
        maturity = "learned"
    elif observed_events >= 3:
        maturity = "observed"
    else:
        maturity = "unseen"

    base.update(
        {
            "ok": True,
            "app_id": app_id,
            "observed_events": int(observed_events or 0),
            "procedures": int(procedures or 0),
            "last_seen": last_seen,
            "maturity": maturity,
        }
    )
    return base
