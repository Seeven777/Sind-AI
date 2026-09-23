import re
from pathlib import Path


APP_RULES = [
    {
        "id": "jarvis",
        "label": "Jarvis Habitat",
        # Do not identify every python/pythonw process as Jarvis. The title is the
        # stable discriminator for the desktop shell.
        "processes": set(),
        "title_terms": ("jarvis habitat", "sind ai"),
    },
    {
        "id": "photoshop",
        "label": "Adobe Photoshop",
        "processes": {"photoshop.exe", "photoshop"},
        "title_terms": ("adobe photoshop", "photoshop"),
    },
    {
        "id": "vscode",
        "label": "Visual Studio Code",
        "processes": {"code.exe", "code"},
        "title_terms": ("visual studio code",),
    },
    {
        "id": "visual_studio",
        "label": "Visual Studio",
        "processes": {"devenv.exe", "devenv"},
        "title_terms": ("microsoft visual studio",),
    },
    {
        "id": "chrome",
        "label": "Google Chrome",
        "processes": {"chrome.exe", "chrome"},
        "title_terms": ("google chrome",),
    },
    {
        "id": "edge",
        "label": "Microsoft Edge",
        "processes": {"msedge.exe", "msedge"},
        "title_terms": ("microsoft edge",),
    },
    {
        "id": "opera",
        "label": "Opera",
        "processes": {"opera.exe", "opera"},
        "title_terms": ("opera",),
    },
    {
        "id": "explorer",
        "label": "Explorador de Arquivos",
        "processes": {"explorer.exe", "explorer"},
        "title_terms": (),
    },
    {
        "id": "powershell",
        "label": "PowerShell",
        "processes": {"powershell.exe", "pwsh.exe", "powershell", "pwsh"},
        "title_terms": ("powershell",),
    },
    {
        "id": "cmd",
        "label": "Prompt de Comando",
        "processes": {"cmd.exe", "cmd"},
        "title_terms": ("command prompt", "prompt de comando"),
    },
    {
        "id": "word",
        "label": "Microsoft Word",
        "processes": {"winword.exe", "winword"},
        "title_terms": ("word",),
    },
    {
        "id": "excel",
        "label": "Microsoft Excel",
        "processes": {"excel.exe", "excel"},
        "title_terms": ("excel",),
    },
    {
        "id": "obs",
        "label": "OBS Studio",
        "processes": {"obs64.exe", "obs32.exe", "obs64", "obs32"},
        "title_terms": ("obs studio",),
    },
]


def identify_app(process_name="", window_title=""):
    proc = str(process_name or "").strip().lower()
    title = str(window_title or "").strip().lower()
    for rule in APP_RULES:
        if proc and proc in rule["processes"]:
            return {"id": rule["id"], "label": rule["label"]}
        if any(term in title for term in rule.get("title_terms", ())):
            return {"id": rule["id"], "label": rule["label"]}
    if proc:
        stem = Path(proc).stem or proc
        return {"id": re.sub(r"[^a-z0-9_-]+", "_", stem.lower()), "label": stem}
    return {"id": "unknown", "label": "Aplicativo desconhecido"}


def infer_document_hint(app_id, window_title):
    """Best-effort document/project hint. It does not read application contents."""
    title = str(window_title or "").strip()
    if not title:
        return ""

    app_id = str(app_id or "").lower()
    cleaned = title
    suffixes = {
        "photoshop": (" - Adobe Photoshop", " — Adobe Photoshop"),
        "vscode": (" - Visual Studio Code", " — Visual Studio Code"),
        "visual_studio": (" - Microsoft Visual Studio", " — Microsoft Visual Studio"),
        "word": (" - Word", " — Word"),
        "excel": (" - Excel", " — Excel"),
        "chrome": (" - Google Chrome", " — Google Chrome"),
        "edge": (" - Microsoft Edge", " — Microsoft Edge"),
        "opera": (" - Opera", " — Opera"),
    }
    for suffix in suffixes.get(app_id, ()):
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].strip()
            break

    if app_id == "photoshop":
        # Photoshop often adds zoom/layer metadata after the filename.
        cleaned = re.sub(r"\s*@\s*\d+(?:\.\d+)?%.*$", "", cleaned).strip()

    return cleaned[:500]
